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
from jinja2 import Template
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
        self.model_name = 'gemini-2.5-flash'  # Stable model with better free tier limits

        # Load resume template
        self.template_path = self.project_root / "templates" / "resume_template.tex"
        self.load_template()

        # Load configuration
        self.config_path = Path(__file__).parent / "tailor_config.yaml"
        self.load_config()

        # Output directory
        self.output_dir = self.project_root / "tailored_resumes"
        self.output_dir.mkdir(exist_ok=True)

    def load_template(self):
        """Load the LaTeX resume template"""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Resume template not found at {self.template_path}")

        with open(self.template_path, 'r', encoding='utf-8') as f:
            self.template_content = f.read()

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
        """Tailor the professional summary for the specific job"""
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
- Focus on value proposition for THIS specific role

Return ONLY the rewritten summary, no explanations.
"""

        return self._call_api_with_retry(prompt).strip()

    def tailor_projects(self,
                       original_projects: List[Dict],
                       job_description: str,
                       company_name: str,
                       role_title: str) -> List[Dict]:
        """Tailor projects to highlight most relevant ones and reframe bullets"""

        # First, select the most relevant projects (max 3-4)
        projects_summary = "\n\n".join([
            f"Project: {p['title']}\nTech: {p['tech']}\n" +
            "\n".join([f"- {b}" for b in p['bullets']])
            for p in original_projects
        ])

        prompt = f"""
You are a professional resume writer. Given these projects and a target job, select the 2-3 most relevant projects and reframe their bullet points.

Original Projects:
{projects_summary}

Target Company: {company_name}
Target Role: {role_title}

Job Description:
{job_description}

Requirements:
1. Select the 2-3 projects most relevant to this job
2. For each selected project, rewrite the bullets to emphasize relevant skills
3. Use JD keywords naturally
4. Do NOT fabricate achievements - only reframe existing ones
5. Keep technical accuracy
6. Each bullet should be one concise, impactful line

Return in this EXACT format:
PROJECT: [Project Title]
TECH: [Technologies]
URL: [GitHub URL]
- Bullet point 1
- Bullet point 2
- Bullet point 3

PROJECT: [Next Project Title]
...
"""

        response_text = self._call_api_with_retry(prompt)

        # Parse the response into project dictionaries
        tailored_projects = []
        current_project = None

        for line in response_text.strip().split('\n'):
            line = line.strip()
            if line.startswith('PROJECT:'):
                if current_project:
                    tailored_projects.append(current_project)
                current_project = {'bullets': [], 'title': line.replace('PROJECT:', '').strip()}
            elif line.startswith('TECH:'):
                if current_project:
                    current_project['tech'] = line.replace('TECH:', '').strip()
            elif line.startswith('URL:'):
                if current_project:
                    current_project['url'] = line.replace('URL:', '').strip()
            elif line.startswith('-') and current_project:
                current_project['bullets'].append(line[1:].strip())

        if current_project:
            tailored_projects.append(current_project)

        # Fallback: if parsing failed, use original projects
        if not tailored_projects:
            print("⚠️  AI response parsing failed, using original projects")
            return original_projects[:3]

        return tailored_projects

    def tailor_skills(self,
                      original_skills: Dict[str, str],
                      job_description: str) -> Dict[str, str]:
        """Reorder and emphasize skills based on JD requirements"""

        skills_text = "\n".join([f"{cat}: {skills}" for cat, skills in original_skills.items()])

        prompt = f"""
Reorder and emphasize this skills list based on the job requirements. Keep the same categories.

Current Skills:
{skills_text}

Job Description:
{job_description}

Requirements:
- Prioritize skills mentioned in the JD within each category
- Keep the same category structure
- Stay truthful - only include skills from the original list
- You can reorder within categories

Return in this EXACT format:
Languages: skill1, skill2, skill3
AI/ML Frameworks: skill1, skill2, skill3
Backend/Cloud: skill1, skill2, skill3
Core Concepts: skill1, skill2, skill3
Databases: skill1, skill2, skill3
Developer Tools: skill1, skill2, skill3
"""

        response_text = self._call_api_with_retry(prompt)

        # Parse response back into dictionary
        tailored_skills = {}
        for line in response_text.strip().split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                # Map back to config keys
                key_map = {
                    'Languages': 'languages',
                    'AI/ML Frameworks': 'ai_ml',
                    'Backend/Cloud': 'backend_cloud',
                    'Core Concepts': 'core_concepts',
                    'Databases': 'databases',
                    'Developer Tools': 'dev_tools'
                }
                config_key = key_map.get(key.strip(), key.strip().lower().replace(' ', '_').replace('/', '_'))
                tailored_skills[config_key] = value.strip()

        # Fallback: if parsing failed, return original
        if not tailored_skills:
            print("⚠️  Skills parsing failed, using original")
            return original_skills

        return tailored_skills

    def generate_tailored_resume(self,
                                company_name: str,
                                role_title: str,
                                job_description: str) -> str:
        """Generate a complete tailored resume using config data"""

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
        print(f"New Summary:\n{tailored_summary[:150]}...\n")

        # Tailor projects
        print("🔧 Selecting and reframing projects...")
        tailored_projects = self.tailor_projects(
            self.config['original_projects'],
            job_description,
            company_name,
            role_title
        )
        print(f"Selected {len(tailored_projects)} most relevant projects\n")

        # Tailor skills
        print("💡 Optimizing skills section...")
        tailored_skills = self.tailor_skills(
            self.config['original_skills'],
            job_description
        )

        # Load template and populate
        template = Template(self.template_content)

        resume_content = template.render(
            summary=tailored_summary,
            projects=tailored_projects,
            skills=tailored_skills
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
