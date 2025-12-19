"""
Resume Tailor - The Brain
Uses Gemini 2.5 Pro to customize resume based on job descriptions
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import google.generativeai as genai
from jinja2 import Template
from datetime import datetime


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
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Load resume template
        self.template_path = self.project_root / "templates" / "resume_template.tex"
        self.load_template()
        
        # Output directory
        self.output_dir = self.project_root / "tailored_resumes"
        self.output_dir.mkdir(exist_ok=True)
    
    def load_template(self):
        """Load the LaTeX resume template"""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Resume template not found at {self.template_path}")
        
        with open(self.template_path, 'r', encoding='utf-8') as f:
            self.template_content = f.read()
    
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
        
        response = self.model.generate_content(prompt)
        return response.text
    
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
        
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def tailor_experience_bullets(self,
                                  original_bullets: List[str],
                                  job_description: str,
                                  company_name: str,
                                  role_title: str) -> List[str]:
        """Tailor experience bullet points to highlight relevant skills"""
        bullets_text = "\n".join([f"- {bullet}" for bullet in original_bullets])
        
        prompt = f"""
You are a professional resume writer. Rewrite these experience bullet points to highlight skills relevant to the target job.

Original Experience Bullets (from Johnson Controls internship):
{bullets_text}

Target Company: {company_name}
Target Role: {role_title}

Job Description Key Requirements:
{job_description}

Requirements:
- Reframe each bullet to emphasize skills mentioned in the JD
- Use action verbs and quantifiable achievements
- Incorporate JD keywords naturally
- Do NOT lie or fabricate achievements
- Keep technical accuracy
- Maintain 4-6 bullet points
- Each bullet should be one concise line

Return ONLY the rewritten bullets in this format:
- Bullet point 1
- Bullet point 2
- Bullet point 3
etc.
"""
        
        response = self.model.generate_content(prompt)
        
        # Parse bullets from response
        bullets = []
        for line in response.text.strip().split('\n'):
            line = line.strip()
            if line.startswith('-'):
                bullets.append(line[1:].strip())
            elif line.startswith('•'):
                bullets.append(line[1:].strip())
            elif line and len(bullets) < 10:  # Max 10 bullets
                bullets.append(line)
        
        return bullets
    
    def tailor_skills(self,
                      original_skills: str,
                      job_description: str) -> str:
        """Reorder and emphasize skills based on JD requirements"""
        prompt = f"""
Reorder and emphasize this skills list based on the job requirements.

Current Skills:
{original_skills}

Job Description:
{job_description}

Requirements:
- Prioritize skills mentioned in the JD
- Add any missing relevant skills you know are common for this role
- Remove or de-emphasize less relevant skills
- Keep format: comma-separated list
- Stay truthful - only include skills someone with this background would reasonably have

Return ONLY the skills list, no explanations.
"""
        
        response = self.model.generate_content(prompt)
        return response.text.strip()
    
    def generate_tailored_resume(self,
                                company_name: str,
                                role_title: str,
                                job_description: str,
                                original_summary: str,
                                original_bullets: List[str],
                                original_skills: str,
                                personal_info: Dict[str, str]) -> str:
        """Generate a complete tailored resume"""
        
        print(f"\n🎯 Tailoring resume for {company_name} - {role_title}")
        print("=" * 60)
        
        # Extract JD requirements
        print("📋 Analyzing job description...")
        jd_summary = self.extract_jd_requirements(job_description)
        print(f"Key Requirements Identified:\n{jd_summary[:200]}...\n")
        
        # Tailor summary
        print("✍️  Tailoring professional summary...")
        tailored_summary = self.tailor_summary(
            original_summary, job_description, company_name, role_title
        )
        print(f"New Summary:\n{tailored_summary}\n")
        
        # Tailor experience bullets
        print("🔧 Reframing experience bullets...")
        tailored_bullets = self.tailor_experience_bullets(
            original_bullets, job_description, company_name, role_title
        )
        print(f"Generated {len(tailored_bullets)} tailored bullets\n")
        
        # Tailor skills
        print("💡 Optimizing skills section...")
        tailored_skills = self.tailor_skills(original_skills, job_description)
        print(f"Skills: {tailored_skills[:100]}...\n")
        
        # Load template and populate
        template = Template(self.template_content)
        
        # Prepare Jinja2 variables
        resume_content = template.render(
            summary=tailored_summary,
            experience_bullets=tailored_bullets,
            skills=tailored_skills,
            **personal_info
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
        
        # Load original resume data (you'll need to populate this)
        original_data = self.load_original_resume_data()
        
        # Generate tailored resume
        return self.generate_tailored_resume(
            company_name=company,
            role_title=title,
            job_description=description,
            original_summary=original_data['summary'],
            original_bullets=original_data['bullets'],
            original_skills=original_data['skills'],
            personal_info=original_data['personal_info']
        )
    
    def load_original_resume_data(self) -> Dict:
        """Load the original resume data
        
        This should be customized with your actual information
        """
        return {
            'summary': """
Computer Engineering student with hands-on experience in industrial automation 
and embedded systems at Johnson Controls. Passionate about AI, robotics, and 
building scalable software systems.
            """.strip(),
            
            'bullets': [
                "Developed PLC control systems for HVAC automation reducing energy consumption by 15%",
                "Implemented embedded C++ firmware for industrial sensors with real-time data processing",
                "Collaborated with cross-functional teams to integrate IoT devices into building management systems",
                "Optimized control algorithms improving system response time by 30%",
                "Conducted system testing and validation ensuring 99.9% uptime in production environments"
            ],
            
            'skills': "Python, C++, Embedded Systems, PLC Programming, IoT, HVAC Controls, Real-time Systems, Git, Linux",
            
            'personal_info': {
                'name': 'Your Name',
                'email': 'your.email@example.com',
                'phone': '+1-234-567-8900',
                'github': 'yourgithub',
                'linkedin': 'yourlinkedin'
            }
        }


def main():
    """Example usage"""
    
    # Example job description
    sample_jd = """
    Sony is looking for New Graduate Software Engineers to join our AI and Creative Technologies division.
    
    Responsibilities:
    - Develop AI-powered creative tools for content creators
    - Work on computer vision and machine learning models
    - Build scalable cloud-based applications
    - Collaborate with designers and product teams
    
    Required Skills:
    - Strong programming skills in Python or C++
    - Understanding of machine learning and AI concepts
    - Experience with cloud platforms (AWS, Azure, GCP)
    - Passion for creative technology and innovation
    
    Preferred:
    - Experience with PyTorch or TensorFlow
    - Knowledge of computer vision or NLP
    - Previous internship experience in tech
    """
    
    try:
        tailor = ResumeTailor()
        
        output_path = tailor.generate_tailored_resume(
            company_name="Sony",
            role_title="New Graduate Software Engineer - AI & Creative Tech",
            job_description=sample_jd,
            original_summary="Computer Engineering student with hands-on experience in industrial automation and embedded systems at Johnson Controls.",
            original_bullets=[
                "Developed PLC control systems for HVAC automation reducing energy consumption by 15%",
                "Implemented embedded C++ firmware for industrial sensors with real-time data processing",
                "Collaborated with cross-functional teams to integrate IoT devices into building management systems",
                "Optimized control algorithms improving system response time by 30%"
            ],
            original_skills="Python, C++, Embedded Systems, PLC Programming, IoT, HVAC Controls, Real-time Systems, Git, Linux",
            personal_info={
                'name': 'Your Name',
                'email': 'your.email@example.com',
                'phone': '+1-234-567-8900',
                'github': 'yourgithub',
                'linkedin': 'yourlinkedin'
            }
        )
        
        print(f"\n🎉 Success! Review your tailored resume at:\n{output_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
