"""
Test script for Resume Tailor
Demonstrates the tailoring functionality with sample data
"""

import os
from resume_tailor import ResumeTailor


def test_sony():
    """Test tailoring for Sony AI role"""

    sony_jd = """
    Sony is seeking New Graduate Software Engineers for our AI and Creative Technologies division.

    You will work on:
    - Developing AI-powered creative tools using Python and machine learning frameworks
    - Building computer vision systems for content analysis and generation
    - Creating scalable cloud-based applications on AWS/Azure
    - Collaborating with designers and product teams on innovative features

    Required Qualifications:
    - Strong programming skills in Python or C++
    - Understanding of machine learning concepts and neural networks
    - Experience with modern development tools (Git, Docker, CI/CD)
    - Bachelor's degree in Computer Science, Engineering, or related field

    Preferred Qualifications:
    - Hands-on experience with PyTorch, TensorFlow, or similar ML frameworks
    - Knowledge of computer vision, NLP, or generative AI
    - Previous internship in software engineering or AI
    - Passion for creative technology and innovation

    We value engineers who can bridge technical excellence with creative thinking.
    """

    original_data = {
        'summary': "Computer Engineering student with hands-on experience in industrial automation and embedded systems at Johnson Controls. Strong programming skills in Python and C++.",

        'bullets': [
            "Developed PLC control systems for HVAC automation reducing energy consumption by 15%",
            "Implemented embedded C++ firmware for industrial sensors with real-time data processing",
            "Collaborated with cross-functional teams to integrate IoT devices into building management systems",
            "Optimized control algorithms improving system response time by 30%",
            "Conducted system testing and validation ensuring 99.9% uptime in production"
        ],

        'skills': "Python, C++, Embedded Systems, PLC Programming, IoT, HVAC Controls, Real-time Systems, Git, Linux",

        'personal_info': {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '+1-234-567-8900',
            'github': 'testuser',
            'linkedin': 'testuser'
        }
    }

    tailor = ResumeTailor()

    output_path = tailor.generate_tailored_resume(
        company_name="Sony",
        role_title="New Graduate Software Engineer - AI & Creative Tech",
        job_description=sony_jd,
        **original_data
    )

    print(f"\n✅ Sony resume generated: {output_path}")


def test_woven():
    """Test tailoring for Woven by Toyota (Industrial/Safety)"""

    woven_jd = """
    Woven by Toyota is hiring New Graduate Engineers for our Autonomous Driving division.

    Responsibilities:
    - Develop safety-critical embedded software for autonomous vehicles
    - Implement real-time control systems for vehicle dynamics
    - Work on sensor fusion and perception algorithms
    - Ensure ISO 26262 compliance in safety-critical systems

    Required Skills:
    - Strong C++ and embedded systems programming
    - Understanding of real-time operating systems (RTOS)
    - Knowledge of control systems and algorithms
    - Experience with hardware interfaces and sensor integration

    Preferred:
    - Automotive industry experience or internship
    - Knowledge of functional safety standards (ISO 26262)
    - Experience with CAN bus, LIN, or other automotive protocols
    - Robotics or mechatronics background
    """

    original_data = {
        'summary': "Computer Engineering student with hands-on experience in industrial automation and embedded systems at Johnson Controls.",

        'bullets': [
            "Developed PLC control systems for HVAC automation reducing energy consumption by 15%",
            "Implemented embedded C++ firmware for industrial sensors with real-time data processing",
            "Collaborated with cross-functional teams to integrate IoT devices into building management systems",
            "Optimized control algorithms improving system response time by 30%",
            "Conducted system testing and validation ensuring 99.9% uptime in production"
        ],

        'skills': "Python, C++, Embedded Systems, PLC Programming, IoT, HVAC Controls, Real-time Systems, Git, Linux",

        'personal_info': {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '+1-234-567-8900',
            'github': 'testuser',
            'linkedin': 'testuser'
        }
    }

    tailor = ResumeTailor()

    output_path = tailor.generate_tailored_resume(
        company_name="Woven by Toyota",
        role_title="New Graduate Engineer - Autonomous Driving",
        job_description=woven_jd,
        **original_data
    )

    print(f"\n✅ Woven resume generated: {output_path}")


def main():
    """Run tests"""

    # Check API key
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ Set GEMINI_API_KEY environment variable first!")
        return

    print("=" * 80)
    print("🧪 TESTING RESUME TAILOR")
    print("=" * 80)
    print("\nThis will generate TWO tailored resumes from the SAME experience:")
    print("1. Sony (AI/Creative focus)")
    print("2. Woven (Industrial/Safety focus)")
    print("\nNotice how the SAME Johnson Controls experience is reframed differently!")
    print("=" * 80)

    input("\nPress Enter to continue...")

    print("\n\n🎨 Test 1: Sony (AI & Creative Tech)")
    print("-" * 80)
    test_sony()

    print("\n\n🚗 Test 2: Woven by Toyota (Autonomous Driving)")
    print("-" * 80)
    test_woven()

    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETE!")
    print("=" * 80)
    print("\nCheck the tailored_resumes/ folder to see the results.")
    print("Compare how the same experience is reframed for different roles!")


if __name__ == "__main__":
    main()
