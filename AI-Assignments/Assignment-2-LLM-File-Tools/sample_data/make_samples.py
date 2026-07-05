"""Generate dummy resume files for the assistant to operate on.

Run:  python sample_data/make_samples.py
Writes 8 .txt resumes into sample_data/resumes/ (idempotent).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RESUMES = os.path.join(HERE, "resumes")

# (filename, name, title, years, skills, summary)
PEOPLE = [
    ("resume_john_doe.txt", "John Doe", "Senior Backend Engineer", 7,
     ["Python", "Django", "PostgreSQL", "Docker", "AWS", "REST APIs"],
     "Backend engineer with 7 years building scalable Python services and APIs."),
    ("resume_jane_smith.txt", "Jane Smith", "Frontend Engineer", 4,
     ["JavaScript", "React", "TypeScript", "CSS", "Jest"],
     "Frontend engineer focused on accessible, performant React applications."),
    ("resume_amir_khan.txt", "Amir Khan", "Data Scientist", 5,
     ["Python", "pandas", "scikit-learn", "SQL", "TensorFlow"],
     "Data scientist with 5 years of experience in ML modeling and analytics."),
    ("resume_maria_garcia.txt", "Maria Garcia", "Full-Stack Engineer", 6,
     ["Python", "Flask", "React", "PostgreSQL", "Docker", "Kubernetes"],
     "Full-stack engineer comfortable across Python backends and React frontends."),
    ("resume_wei_chen.txt", "Wei Chen", "DevOps Engineer", 8,
     ["AWS", "Terraform", "Kubernetes", "Python", "CI/CD", "Linux"],
     "DevOps engineer specializing in cloud infrastructure and automation."),
    ("resume_olga_petrova.txt", "Olga Petrova", "Machine Learning Engineer", 3,
     ["Python", "PyTorch", "NLP", "Docker", "FastAPI"],
     "ML engineer building NLP systems and deploying models with FastAPI."),
    ("resume_sam_okoro.txt", "Sam Okoro", "Junior Software Engineer", 2,
     ["Java", "Spring", "SQL", "Git"],
     "Junior engineer with 2 years of Java/Spring backend experience."),
    ("resume_lena_muller.txt", "Lena Müller", "Mobile Engineer", 5,
     ["Kotlin", "Android", "Java", "REST APIs", "Firebase"],
     "Mobile engineer shipping Android apps used by millions of users."),
]

TEMPLATE = """\
{name}
{title}

SUMMARY
{summary}

SKILLS
{skills}

EXPERIENCE
- {years} years of professional software engineering experience.
- Collaborated with cross-functional teams to design, build, and ship features.
- Wrote automated tests and participated in code review.

EDUCATION
- B.S. in Computer Science

CONTACT
- email: {email}
"""


def main() -> None:
    os.makedirs(RESUMES, exist_ok=True)
    for fname, name, title, years, skills, summary in PEOPLE:
        email = fname.replace("resume_", "").replace(".txt", "").replace("_", ".")
        text = TEMPLATE.format(
            name=name, title=title, summary=summary, years=years,
            skills=", ".join(skills), email=f"{email}@example.com",
        )
        with open(os.path.join(RESUMES, fname), "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"Wrote {len(PEOPLE)} resumes to {RESUMES}")


if __name__ == "__main__":
    main()
