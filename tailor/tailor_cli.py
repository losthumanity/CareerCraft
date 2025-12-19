"""
Resume Tailor CLI - Interactive interface for tailoring resumes
"""

import sys
import argparse
from pathlib import Path
import yaml
from resume_tailor import ResumeTailor


def load_config():
    """Load tailor configuration"""
    config_path = Path(__file__).parent / "tailor_config.yaml"

    if not config_path.exists():
        print("❌ Configuration file not found. Please create tailor_config.yaml")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def tailor_from_file(args):
    """Tailor resume from a JD text file"""

    # Read job description
    jd_path = Path(args.jd_file)
    if not jd_path.exists():
        print(f"❌ Job description file not found: {jd_path}")
        sys.exit(1)

    with open(jd_path, 'r', encoding='utf-8') as f:
        jd_content = f.read()

    # Initialize tailor
    tailor = ResumeTailor()

    # Generate tailored resume
    output_path = tailor.generate_tailored_resume(
        company_name=args.company,
        role_title=args.role,
        job_description=jd_content
    )

    print(f"\n✅ Done! Your tailored resume: {output_path}")


def tailor_from_db(args):
    """Tailor resume from a job in the database"""

    tailor = ResumeTailor()

    try:
        output_path = tailor.generate_from_db_job(args.job_id)
        print(f"\n✅ Done! Your tailored resume: {output_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def interactive_mode():
    """Interactive mode for tailoring resumes"""
    config = load_config()

    print("=" * 60)
    print("🎯 RESUME TAILOR - Interactive Mode")
    print("=" * 60)
    print()

    # Get inputs
    company = input("Company Name: ").strip()
    role = input("Role Title: ").strip()

    print("\nPaste the Job Description (press Ctrl+D or Ctrl+Z+Enter when done):")
    print("-" * 60)

    jd_lines = []
    try:
        while True:
            line = input()
            jd_lines.append(line)
    except EOFError:
        pass

    jd_content = '\n'.join(jd_lines).strip()

    if not company or not role or not jd_content:
        print("\n❌ All fields are required!")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🚀 Generating tailored resume...")
    print("=" * 60)

    # Initialize tailor
    tailor = ResumeTailor()

    # Generate
    output_path = tailor.generate_tailored_resume(
        company_name=company,
        role_title=role,
        job_description=jd_content

    print(f"\n✅ Success! Your tailored resume: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Resume Tailor - Customize your resume for specific jobs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python tailor_cli.py

  # From job description file
  python tailor_cli.py --file sony_jd.txt --company "Sony" --role "Software Engineer"

  # From database job
  python tailor_cli.py --db --job-id 5
        """
    )

    parser.add_argument('--file', dest='jd_file',
                       help='Path to job description text file')
    parser.add_argument('--company',
                       help='Company name (required with --file)')
    parser.add_argument('--role',
                       help='Role title (required with --file)')
    parser.add_argument('--db', action='store_true',
                       help='Tailor from database job')
    parser.add_argument('--job-id', type=int,
                       help='Job ID from database (required with --db)')

    args = parser.parse_args()

    # Check for API key
    import os
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY environment variable not set!")
        print("\nSet it in your .env file or environment:")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        sys.exit(1)

    # Route to appropriate handler
    if args.jd_file:
        if not args.company or not args.role:
            print("❌ --company and --role are required with --file")
            sys.exit(1)
        tailor_from_file(args)
    elif args.db:
        if not args.job_id:
            print("❌ --job-id is required with --db")
            sys.exit(1)
        tailor_from_db(args)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
