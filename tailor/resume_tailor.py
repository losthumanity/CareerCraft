"""
Resume Tailor - The Brain
Uses Gemini 2.0 Flash to customize resume based on job descriptions
Updated to work with Pranav's project-based resume format
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from google import genai
from google.genai import types
from datetime import datetime
import time

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip


class ResumeTailor:
    """Tailors resume content based on job descriptions using Gemini"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the Resume Tailor

        Args:
            config_path: Path to config file with API keys
        """
        self.project_root = Path(__file__).parent.parent

        # Load API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set.\n"
                "Set it in .env file or environment:\n"
                "  PowerShell: $env:GEMINI_API_KEY='your-key'\n"
                "  Or add to .env: GEMINI_API_KEY=your-key"
            )

        # Configure Gemini client with new API
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-2.5-flash'  # Use the experimental model

        # Load configuration
        self.config_path = Path(__file__).parent / "tailor_config.yaml"
        self.load_config()

        # Load base template structure
        self.template_path = self.project_root / "templates" / "resume_template.tex"
        self.load_base_template()

        # Output directory
        self.output_dir = self.project_root / "tailored_resumes"
        self.output_dir.mkdir(exist_ok=True)

    def load_base_template(self):
        """Load the base LaTeX template structure"""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Resume template not found at {self.template_path}")

        with open(self.template_path, 'r', encoding='utf-8') as f:
            self.base_template = f.read()

    def load_config(self):
        """Load the tailor configuration"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def extract_jd_requirements(self, job_description: str) -> str:
        """Extract key requirements from job description using Gemini"""
        prompt = f"""
Analyze this job description and extract:
1. Key technical skills required
2. Main responsibilities
3. Important keywords that should appear in a tailored resume
4. Soft skills mentioned

Job Description:
{job_description}

Provide a concise summary focused on what matters for resume tailoring.
"""

        return self._call_api_with_retry(prompt)

    def _call_api_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Call Gemini API with retry logic for rate limits and server errors"""
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                if '503' in error_str or 'overloaded' in error_str.lower():
                    wait_time = (attempt + 1) * 3  # 3s, 6s, 9s
                    print(f"⚠️  Server overloaded, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                elif '429' in error_str or 'quota' in error_str.lower():
                    wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                    print(f"⚠️  Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    raise  # Re-raise if not a retryable error

        # If all retries failed
        raise Exception(f"API call failed after {max_retries} retries. Please try again later.")

    def tailor_summary(self,
                       original_summary: str,
                       job_description: str,
                       company_name: str,
                       role_title: str) -> str:
        """Tailor the professional summary for the specific job - returns LaTeX code"""
        prompt = f"""
You are a professional resume writer. Rewrite this professional summary to align with the job description.

Original Summary:
{original_summary}

Target Company: {company_name}
Target Role: {role_title}

Job Description:
{job_description}

Requirements:
- Keep it concise (3-4 lines max)
- Use keywords from the JD naturally
- Highlight relevant skills and experiences
- Do NOT fabricate experience or skills
- Maintain professional tone

Return ONLY the text content (no LaTeX commands, just the paragraph text).
"""

        return self._call_api_with_retry(prompt).strip()

    def tailor_projects(self,
                       original_projects: List[Dict],
                       job_description: str,
                       company_name: str,
                       role_title: str) -> str:
        """Tailor projects - returns complete LaTeX code for projects section"""

        projects_summary = "\n\n".join([
            f"Project: {p['title']}\nTech: {p['tech']}\nURL: {p.get('url', '')}\n" +
            "\n".join([f"- {b}" for b in p['bullets']])
            for p in original_projects
        ])

        prompt = f"""
You are a LaTeX resume expert. Select 2-3 most relevant projects and generate complete LaTeX code.

Original Projects:
{projects_summary}

Target Company: {company_name}
Target Role: {role_title}
Job Description: {job_description}

Generate LaTeX code using this EXACT structure for each project:
     \\resumeProjectHeading
          {{\\href{{PROJECT_URL}}{{\\textbf{{\\large{{\\underline{{PROJECT_TITLE}}}}}} \\faExternalLink}} $|$ \\large{{\\underline{{TECHNOLOGIES}}}}}}{{}}\\\\
          \\resumeItemListStart
            \\resumeItem{{\\normalsize{{Bullet point 1}}}}
            \\resumeItem{{\\normalsize{{Bullet point 2}}}}
            \\resumeItem{{\\normalsize{{Bullet point 3}}}}
          \\resumeItemListEnd
          \\vspace{{-13pt}}

Requirements:
- Select 2-3 most relevant projects for this role
- Rewrite bullets to emphasize JD keywords
- Use proper LaTeX escaping (\\%, \\&, etc.)
- Keep bullets concise and impactful
- Do NOT add markdown formatting
- Return ONLY the LaTeX code, no explanations

Start with the first \\resumeProjectHeading and end after the last \\vspace{{-13pt}}
"""

        return self._call_api_with_retry(prompt)

    def tailor_skills(self,
                      original_skills: Dict[str, str],
                      job_description: str) -> str:
        """Reorder skills based on JD - returns complete LaTeX code"""

        skills_text = "\n".join([f"{cat}: {skills}" for cat, skills in original_skills.items()])

        prompt = f"""
You are a LaTeX resume expert. Reorder these skills to prioritize those in the job description.

Current Skills:
{skills_text}

Job Description:
{job_description}

Generate LaTeX code using this EXACT structure:
     \\textbf{{\\normalsize{{Languages:}}}}{{  \\normalsize{{skill1, skill2, skill3}}}} \\\\
     \\textbf{{\\normalsize{{AI/ML Frameworks:}}}}{{  \\normalsize{{skill1, skill2, skill3}}}} \\\\
     \\textbf{{\\normalsize{{Backend/Cloud: }}}}{{  \\normalsize{{skill1, skill2, skill3}}}} \\\\
     \\textbf{{\\normalsize{{Core Concepts:}}}}{{  \\normalsize{{skill1, skill2, skill3}}}} \\\\
     \\textbf{{\\normalsize{{Databases:}}}}{{  \\normalsize{{skill1, skill2, skill3}}}} \\\\
     \\textbf{{\\normalsize{{Developer Tools:}}}}
    {{\\normalsize{{skill1, skill2, skill3}}}} \\\\

Requirements:
- Prioritize JD-mentioned skills within each category
- Keep all 6 categories
- Use only skills from the original list
- Return ONLY the LaTeX code, no explanations
"""

        return self._call_api_with_retry(prompt)

    def generate_tailored_resume(self,
                                company_name: str,
                                role_title: str,
                                job_description: str) -> str:
        """Generate a complete tailored resume using direct LaTeX generation"""

        print(f"\n🎯 Tailoring resume for {company_name} - {role_title}")
        print("=" * 60)

        # Extract JD requirements
        print("📋 Analyzing job description...")
        jd_summary = self.extract_jd_requirements(job_description)
        print(f"Key Requirements:\n{jd_summary[:200]}...\n")

        # Tailor summary
        print("✍️  Tailoring professional summary...")
        tailored_summary = self.tailor_summary(
            self.config['original_summary'],
            job_description,
            company_name,
            role_title
        )

        # Tailor projects (get LaTeX code directly)
        print("🔧 Selecting and reframing projects...")
        projects_latex = self.tailor_projects(
            self.config['original_projects'],
            job_description,
            company_name,
            role_title
        )

        # Tailor skills (get LaTeX code directly)
        print("💡 Optimizing skills section...")
        skills_latex = self.tailor_skills(
            self.config['original_skills'],
            job_description
        )

        # Replace sections in base template
        resume_content = self.base_template

        # Replace summary
        resume_content = resume_content.replace(
            "{{SUMMARY_PLACEHOLDER}}",
            tailored_summary
        )

        # Replace projects
        resume_content = resume_content.replace(
            "{{PROJECTS_PLACEHOLDER}}",
            projects_latex.strip()
        )

        # Replace skills
        resume_content = resume_content.replace(
            "{{SKILLS_PLACEHOLDER}}",
            skills_latex.strip()
        )

        # Save to file
        safe_company = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
        safe_role = re.sub(r'[^\w\s-]', '', role_title).strip().replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        output_filename = f"{safe_company}_{safe_role}_{timestamp}.tex"
        output_path = self.output_dir / output_filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(resume_content)

        print(f"✅ Tailored resume saved to: {output_path}")
        print("=" * 60)

        return str(output_path)

    def generate_from_db_job(self, job_id: int, db_path: Optional[str] = None):
        """Generate tailored resume from a job in the database

        Args:
            job_id: ID of the job in the watcher database
            db_path: Optional path to database file
        """
        import sqlite3

        if db_path is None:
            db_path = self.project_root / "watcher" / "jobs.db"

        # Fetch job details
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT company, title, description, url
            FROM jobs
            WHERE id = ?
        """, (job_id,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            raise ValueError(f"Job with ID {job_id} not found in database")

        company, title, description, url = result

        # Generate tailored resume
        return self.generate_tailored_resume(
            company_name=company,
            role_title=title,
            job_description=description
        )


def main():
    """Example usage with sample job description"""

    sample_jd = """
    Woven by Toyota is hiring New Graduate Engineers for our Autonomous Driving Software division.

    Responsibilities:
    - Develop safety-critical embedded software for autonomous vehicles
    - Implement real-time control systems and algorithms
    - Work on perception and sensor fusion pipelines
    - Collaborate with hardware teams on system integration

    Required Skills:
    - Strong programming skills in Python and C++
    - Understanding of machine learning for perception systems
    - Experience with real-time systems and embedded programming
    - Knowledge of software engineering best practices

    Preferred:
    - Experience with computer vision or deep learning
    - Familiarity with ROS, Docker, or cloud platforms
    - Previous internship or project experience
    """

    try:
        tailor = ResumeTailor()

        output_path = tailor.generate_tailored_resume(
            company_name="Woven by Toyota",
            role_title="New Graduate Engineer - Autonomous Driving",
            job_description=sample_jd
        )

        print(f"\n🎉 Success! Review your tailored resume at:\n{output_path}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
