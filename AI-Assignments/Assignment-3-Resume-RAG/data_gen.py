"""
data_gen.py
===========
Generate a diverse, deterministic dataset for the Resume RAG system:

  * data/resumes/*.txt      — 33 resumes across 11 roles (section-structured)
  * data/jobs/*.txt         — 6 job descriptions
  * data/ground_truth.json  — {job_id: [relevant candidate ids]} for metrics

Relevance label = a candidate is "relevant" to a job if the candidate's role
matches the job's target role. This gives the retrieval-accuracy metrics
(precision@k / recall / MRR) a well-defined gold set.

Run:  python data_gen.py
"""

from __future__ import annotations

import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RESUME_DIR = os.path.join(DATA, "resumes")
JOB_DIR = os.path.join(DATA, "jobs")
GROUND_TRUTH = os.path.join(DATA, "ground_truth.json")

# role -> (title, core skills pool, education pool)
ROLES = {
    "backend": ("Backend Engineer",
                ["Python", "Django", "Flask", "PostgreSQL", "Redis", "REST APIs",
                 "Docker", "Microservices", "RabbitMQ"]),
    "frontend": ("Frontend Engineer",
                 ["JavaScript", "TypeScript", "React", "Redux", "CSS", "HTML",
                  "Next.js", "Jest", "Webpack"]),
    "data_scientist": ("Data Scientist",
                       ["Python", "pandas", "NumPy", "scikit-learn", "SQL",
                        "Statistics", "Matplotlib", "Jupyter", "A/B Testing"]),
    "ml_engineer": ("Machine Learning Engineer",
                    ["Python", "PyTorch", "TensorFlow", "NLP", "MLflow",
                     "Docker", "FastAPI", "Kubernetes", "Feature Engineering"]),
    "devops": ("DevOps Engineer",
               ["AWS", "Terraform", "Kubernetes", "Docker", "CI/CD", "Linux",
                "Ansible", "Prometheus", "Bash"]),
    "data_engineer": ("Data Engineer",
                      ["Python", "Spark", "Airflow", "SQL", "Kafka", "AWS",
                       "ETL", "Snowflake", "dbt"]),
    "mobile": ("Mobile Engineer",
               ["Kotlin", "Swift", "Android", "iOS", "Java", "REST APIs",
                "Firebase", "Jetpack Compose"]),
    "fullstack": ("Full-Stack Engineer",
                  ["Python", "React", "TypeScript", "PostgreSQL", "Docker",
                   "Node.js", "REST APIs", "AWS"]),
    "security": ("Security Engineer",
                 ["Python", "Penetration Testing", "SIEM", "Networking",
                  "Cryptography", "Linux", "Incident Response", "OWASP"]),
    "qa": ("QA Automation Engineer",
           ["Python", "Selenium", "Cypress", "Pytest", "CI/CD", "API Testing",
            "Java", "TestRail"]),
    "cloud": ("Cloud Architect",
              ["AWS", "Azure", "Terraform", "Kubernetes", "Microservices",
               "Networking", "Python", "Cost Optimization"]),
}

FIRST = ["John", "Jane", "Amir", "Maria", "Wei", "Olga", "Sam", "Lena", "Raj",
         "Sofia", "Tom", "Nina", "Omar", "Priya", "Carlos", "Yuki", "Hassan",
         "Grace", "Diego", "Aisha", "Ivan", "Mei", "Noah", "Elena", "Karim",
         "Rosa", "Leo", "Tara", "Victor", "Anya", "Paul", "Zoe", "Ravi"]
LAST = ["Doe", "Smith", "Khan", "Garcia", "Chen", "Petrova", "Okoro", "Muller",
        "Patel", "Rossi", "Turner", "Novak", "Farah", "Nair", "Diaz", "Tanaka",
        "Ali", "Owens", "Silva", "Hassan", "Volkov", "Wong", "Brown", "Vargas",
        "Aziz", "Lopez", "Meyer", "Quinn", "Ivanov", "Kim", "Walsh", "Adams", "Rao"]
DEGREES = ["B.S. Computer Science", "B.S. Software Engineering",
           "M.S. Computer Science", "B.S. Information Systems",
           "M.S. Data Science", "Bootcamp + B.A. Mathematics"]

RESUME_TEMPLATE = """\
{name}
{title}

SUMMARY
{title} with {years} years of professional experience specializing in {top3}. {blurb}

SKILLS
{skills}

EXPERIENCE
{experience}

EDUCATION
{education}

CONTACT
email: {email}
"""

BLURBS = [
    "Passionate about building reliable, well-tested systems.",
    "Focused on performance, scalability, and clean architecture.",
    "Enjoys mentoring peers and driving technical decisions.",
    "Strong collaborator across product, design, and engineering.",
    "Delivers pragmatic solutions under real-world constraints.",
]


def _experience(role_title: str, years: int, skills, rng) -> str:
    n = min(3, max(1, years // 3 + 1))
    companies = ["Nimbus", "Brightwave", "Corti", "DataForge", "Ellipse",
                 "Fathom", "Harborlight", "Meridian", "Northstar", "Orbital"]
    lines = []
    for _ in range(n):
        used = ", ".join(rng.sample(skills, min(len(skills), rng.randint(2, 4))))
        lines.append(f"- {role_title} @ {rng.choice(companies)}: "
                     f"built and shipped features using {used}.")
    return "\n".join(lines)


def generate(seed: int = 7):
    rng = random.Random(seed)
    os.makedirs(RESUME_DIR, exist_ok=True)
    os.makedirs(JOB_DIR, exist_ok=True)

    role_keys = list(ROLES.keys())
    resumes = []  # (cid, role)
    idx = 0
    # 3 resumes per role => 33 resumes.
    for role in role_keys:
        title, pool = ROLES[role]
        for _ in range(3):
            idx += 1
            first, last = rng.choice(FIRST), rng.choice(LAST)
            years = rng.randint(2, 13)
            k = min(len(pool), rng.randint(5, 7))
            skills = rng.sample(pool, k)
            cid = f"C{idx:03d}_{first}_{last}".replace(" ", "_")
            fname = f"{cid}.txt"
            text = RESUME_TEMPLATE.format(
                name=f"{first} {last}", title=title, years=years,
                top3=", ".join(skills[:3]), blurb=rng.choice(BLURBS),
                skills=", ".join(skills),
                experience=_experience(title, years, skills, rng),
                education=rng.choice(DEGREES),
                email=f"{first.lower()}.{last.lower()}@example.com",
            )
            with open(os.path.join(RESUME_DIR, fname), "w", encoding="utf-8") as fh:
                fh.write(text)
            resumes.append((cid, role))

    # Job descriptions (target role + must-have) — 6 total.
    jobs = [
        ("job_backend_python", "backend",
         "Senior Backend Engineer",
         "We need a Senior Backend Engineer to build scalable APIs and services. "
         "Must have 5+ years of Python, strong Django or Flask experience, and "
         "solid PostgreSQL. Docker and microservices a big plus.",
         ["5+ years Python"]),
        ("job_ml_engineer", "ml_engineer",
         "Machine Learning Engineer",
         "Looking for an ML Engineer to build and deploy NLP models. Must have "
         "Python and PyTorch or TensorFlow. Experience with FastAPI, Docker, and "
         "MLflow for model serving is highly desirable.",
         ["3+ years Python"]),
        ("job_frontend_react", "frontend",
         "Frontend Engineer (React)",
         "Seeking a Frontend Engineer strong in React and TypeScript to build a "
         "fast, accessible web app. Redux, Next.js, and Jest testing are pluses.",
         []),
        ("job_devops_aws", "devops",
         "DevOps / Cloud Engineer",
         "Hiring a DevOps Engineer to own cloud infrastructure. Must have AWS, "
         "Terraform, and Kubernetes. CI/CD pipelines and Linux administration "
         "are core to the role.",
         ["4+ years AWS"]),
        ("job_data_engineer", "data_engineer",
         "Data Engineer",
         "Data Engineer to build batch and streaming pipelines. Must have Python, "
         "Spark, and SQL. Airflow orchestration and Kafka streaming experience "
         "strongly preferred.",
         []),
        ("job_data_scientist", "data_scientist",
         "Data Scientist",
         "Data Scientist to drive product analytics and modeling. Must have "
         "Python, pandas, and scikit-learn, plus solid statistics and SQL. "
         "A/B testing experience is a plus.",
         []),
    ]

    ground_truth = {}
    for job_id, role, title, body, must in jobs:
        with open(os.path.join(JOB_DIR, job_id + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(f"# {title}\n\n{body}\n")
            if must:
                fh.write("\nMust-have: " + "; ".join(must) + "\n")
        ground_truth[job_id] = {
            "target_role": role,
            "must_have": must,
            "relevant": [cid for cid, r in resumes if r == role],
        }

    with open(GROUND_TRUTH, "w", encoding="utf-8") as fh:
        json.dump(ground_truth, fh, indent=2)

    return len(resumes), len(jobs)


if __name__ == "__main__":
    n_r, n_j = generate()
    print(f"Generated {n_r} resumes -> {RESUME_DIR}")
    print(f"Generated {n_j} jobs    -> {JOB_DIR}")
    print(f"Ground truth            -> {GROUND_TRUTH}")
