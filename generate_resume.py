#!/usr/bin/env python3
"""
AI-Powered Resume Adapter MVP
Simple script that takes user profile + job description and generates tailored PDF resume.
"""

import click
import yaml
import json
import os
from pathlib import Path
from jinja2 import Template
import pdfkit
import openai
from dotenv import load_dotenv

config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')


# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("Please set OPENAI_API_KEY environment variable")

client = openai.OpenAI()


def load_user_profile(profile_path):
    """Load user profile from YAML or JSON file."""
    with open(profile_path, 'r', encoding='utf-8') as f:
        if profile_path.endswith('.yaml') or profile_path.endswith('.yml'):
            return yaml.safe_load(f)
        else:
            return json.load(f)


def load_job_description(job_path):
    """Load job description from text file."""
    with open(job_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def tailor_resume_with_llm(user_profile, job_description):
    """Use OpenAI to tailor the resume content to the job."""
    
    prompt = f"""
You are an expert resume writer. Given a user's profile and a job description, create a tailored resume by selecting and reordering the most relevant information.
Do not use all the information in the user's profile. If the skills, experience, or education do not pertain to the job, leave them out. Only include irrelevant information if there is not enough content.
USER PROFILE:
{json.dumps(user_profile, indent=2)}

JOB DESCRIPTION:
{job_description}

Please return a JSON object with the tailored resume content using this structure:
{{
    "name": "Full Name",
    "contact": {{
        "email": "email@example.com",
        "phone": "phone number",
        "location": "city, state",
        "linkedin": "linkedin url",
        "github": "github url"
    }},
    "professional_summary": "2-3 sentence summary tailored to this job",
    "skills": ["skill1", "skill2", "skill3", ...],
    "experience": [
        {{
            "company": "Company Name",
            "position": "Job Title",
            "duration": "Start - End Date",
            "achievements": ["achievement 1", "achievement 2", ...]
        }}
    ],
    "education": [
        {{
            "institution": "School Name",
            "degree": "Degree Type",
            "field": "Field of Study",
            "graduation": "Year"
        }}
    ],
    "projects": [
        {{
            "name": "Project Name",
            "description": "Brief description",
            "technologies": ["tech1", "tech2"]
        }}
    ]
}}

Instructions:
- Only include the most relevant experiences (max 4)
- Prioritize skills that match the job requirements
- Rewrite achievements to use keywords from the job description
- Rewrite project descriptions to use keywords from the job description
- Order everything by relevance to the job
- Keep it concise and ATS-friendly
- Use information from user profile to tailor the professional summary to the job
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert resume writer. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean up JSON if wrapped in markdown
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        return json.loads(response_text)
        
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        # Fallback: return original profile in expected format
        return format_profile_as_resume(user_profile)


def format_profile_as_resume(profile):
    """Convert raw profile to resume format (fallback)."""
    return {
        "name": profile.get("name", ""),
        "contact": profile.get("contact", {}),
        "professional_summary": profile.get("professional_summary", ""),
        "skills": profile.get("skills", []),
        "experience": profile.get("experience", []),
        "education": profile.get("education", []),
        "projects": profile.get("projects", [])
    }


def generate_html_resume(resume_data):
    """Generate HTML resume from template file."""
    template_path = Path("templates/resume_template.html")
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template_str = f.read()
    
    template = Template(template_str)
    return template.render(**resume_data)


def generate_pdf(html_content, output_path):
    """Generate PDF from HTML content using pdfkit."""
    try:
        # Configure pdfkit options for better output
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }
        
        pdfkit.from_string(html_content, output_path, options=options, configuration=config)
        return True
    except Exception as e:
        print(f"Error generating PDF with pdfkit: {e}")
        print("Please make sure wkhtmltopdf is installed:")
        print("Windows: Download from https://wkhtmltopdf.org/downloads.html")
        print("Mac: brew install wkhtmltopdf")
        print("Linux: sudo apt-get install wkhtmltopdf")
        
        # Fallback: save as HTML
        html_output = output_path.replace('.pdf', '.html')
        with open(html_output, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Saved as HTML instead: {html_output}")
        return False


@click.command()
@click.option('--profile', '-p', required=True, help='Path to user profile YAML/JSON file')
@click.option('--job', '-j', required=True, help='Path to job description text file')
@click.option('--output', '-o', required=True, help='Output path for generated PDF resume')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def main(profile, job, output, verbose):
    """Generate a tailored resume PDF from user profile and job description."""
    
    try:
        # Ensure output directory exists
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        
        if verbose:
            click.echo("🚀 Starting resume generation...")
        
        # Load inputs
        if verbose:
            click.echo(f"📖 Loading user profile from {profile}")
        user_profile = load_user_profile(profile)
        
        if verbose:
            click.echo(f"📋 Loading job description from {job}")
        job_description = load_job_description(job)
        
        # Tailor resume with LLM
        if verbose:
            click.echo("🤖 Tailoring resume with AI...")
        tailored_resume = tailor_resume_with_llm(user_profile, job_description)
        
        # Generate HTML
        if verbose:
            click.echo("📄 Generating HTML resume...")
        html_content = generate_html_resume(tailored_resume)
        
        # Generate PDF
        if verbose:
            click.echo("📁 Generating PDF...")
        success = generate_pdf(html_content, output)
        
        if success:
            click.echo(f"✨ Resume generated successfully: {output}")
        else:
            click.echo("❌ Failed to generate PDF", err=True)
            
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)


if __name__ == "__main__":
    main()