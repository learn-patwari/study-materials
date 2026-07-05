"""
data_store.py
=============
Synthetic resume dataset generation and loading.

The assignment references a corpus of ~100 resumes (from earlier milestones).
To keep this submission fully self-contained and reproducible, we generate a
deterministic set of 100 synthetic candidate resumes with a fixed random seed
and persist them to ``data/resumes.json``.

Nothing here depends on network access or API keys, so graders can run the
whole system offline.
"""

from __future__ import annotations

import json
import os
import random
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RESUMES_PATH = os.path.join(DATA_DIR, "resumes.json")
JD_DIR = os.path.join(DATA_DIR, "job_descriptions")

# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------
# Skill vocabulary used both to *generate* resumes and to *extract* requirements
# from a job description (see tools.extract_requirements). Frontend-heavy to
# match the sample "Senior Frontend Engineer" JD, plus general engineering.
SKILL_VOCAB: List[str] = [
    "React", "Redux", "TypeScript", "JavaScript", "Next.js", "Vue.js",
    "Angular", "HTML", "CSS", "Sass", "Tailwind CSS", "GraphQL", "REST",
    "Node.js", "Express", "Jest", "Cypress", "Playwright", "Webpack", "Vite",
    "Storybook", "React Native", "Accessibility", "Web Performance",
    "Python", "Django", "FastAPI", "Java", "Go", "Docker", "Kubernetes",
    "AWS", "GCP", "Azure", "PostgreSQL", "MongoDB", "Redis", "CI/CD",
    "Terraform", "Figma", "Micro-frontends", "WebSockets", "PWA",
]

FIRST_NAMES = [
    "Alice", "Brian", "Carla", "David", "Elena", "Frank", "Grace", "Hassan",
    "Ivy", "Jamal", "Karen", "Liam", "Mei", "Noah", "Olga", "Priya", "Quinn",
    "Rosa", "Sam", "Tara", "Umar", "Vera", "Wei", "Xander", "Yara", "Zane",
    "Nina", "Omar", "Paula", "Ravi", "Sofia", "Theo", "Uma", "Victor",
]
LAST_NAMES = [
    "Anderson", "Brown", "Chen", "Diaz", "Evans", "Fernandez", "Garcia",
    "Hughes", "Ibrahim", "Johnson", "Khan", "Lopez", "Martinez", "Nguyen",
    "Owens", "Patel", "Quinn", "Rossi", "Singh", "Turner", "Ueda", "Vargas",
    "Wong", "Xu", "Yamamoto", "Zhang", "Kim", "Silva", "Murphy", "Novak",
]
COMPANIES = [
    "Nimbus Labs", "Brightwave", "Corti Systems", "DataForge", "Ellipse",
    "Fathom", "Glimmer", "Harborlight", "Ironclad", "Junction", "Kestrel",
    "Lumina", "Meridian", "Northstar", "Orbital", "Pinnacle", "Quantile",
]
DEGREES = [
    "B.S. Computer Science", "B.S. Software Engineering",
    "B.A. Design", "M.S. Computer Science", "B.S. Information Systems",
    "Self-taught / Bootcamp (General Assembly)",
]
LOCATIONS = [
    "Remote", "San Francisco, CA", "Austin, TX", "New York, NY",
    "Seattle, WA", "London, UK", "Berlin, DE", "Bangalore, IN", "Toronto, CA",
]
TITLES = [
    "Frontend Engineer", "Senior Frontend Engineer", "Full-Stack Engineer",
    "Software Engineer", "UI Engineer", "Web Developer",
    "Staff Frontend Engineer", "Junior Frontend Engineer",
]


def _make_candidate(idx: int, rng: random.Random) -> Dict[str, Any]:
    first = rng.choice(FIRST_NAMES)
    last = rng.choice(LAST_NAMES)
    years = rng.randint(0, 14)

    # Skill count scales loosely with experience.
    n_skills = min(len(SKILL_VOCAB), max(4, rng.randint(4, 6) + years // 3))
    skills = rng.sample(SKILL_VOCAB, n_skills)

    title = rng.choice(TITLES)
    if years >= 8 and "Senior" not in title and "Staff" not in title:
        title = "Senior " + title.replace("Junior ", "")

    n_jobs = min(4, max(1, years // 3 + 1))
    experience = []
    remaining = years
    for j in range(n_jobs):
        dur = max(1, remaining // (n_jobs - j)) if (n_jobs - j) else 1
        remaining -= dur
        company = rng.choice(COMPANIES)
        role = rng.choice(TITLES)
        used = rng.sample(skills, min(len(skills), rng.randint(2, 4)))
        highlights = [
            f"Built and shipped features using {', '.join(used)}.",
            f"Collaborated with design and backend teams to deliver "
            f"{rng.choice(['a dashboard', 'a checkout flow', 'an admin portal', 'a mobile web app', 'a design system'])}.",
        ]
        experience.append(
            {"company": company, "role": role, "years": dur, "highlights": highlights}
        )

    summary = (
        f"{title} with {years} years of experience specializing in "
        f"{', '.join(skills[:3])}. Passionate about building performant, "
        f"accessible user interfaces."
    )

    return {
        "id": f"C{idx:03d}",
        "name": f"{first} {last}",
        "title": title,
        "years_experience": years,
        "skills": skills,
        "education": rng.choice(DEGREES),
        "location": rng.choice(LOCATIONS),
        "summary": summary,
        "experience": experience,
    }


def _handcrafted() -> List[Dict[str, Any]]:
    """A few fixed candidates so demo queries have stable, explainable answers.

    In particular the assignment's example query "Why did John rank higher
    than Jane?" needs a John and a Jane with a clear, defensible ranking gap.
    """
    john = {
        "id": "C001",
        "name": "John Carter",
        "title": "Senior Frontend Engineer",
        "years_experience": 6,
        "skills": ["React", "Redux", "TypeScript", "Next.js", "GraphQL",
                   "Jest", "Accessibility", "Web Performance", "CSS"],
        "education": "B.S. Computer Science",
        "location": "Remote",
        "summary": "Senior Frontend Engineer with 6 years building large-scale "
                   "React + TypeScript applications with a focus on performance "
                   "and accessibility.",
        "experience": [
            {"company": "Meridian", "role": "Senior Frontend Engineer", "years": 3,
             "highlights": ["Led migration of a legacy app to React + TypeScript.",
                            "Cut initial load time by 40% via code-splitting and lazy loading."]},
            {"company": "Brightwave", "role": "Frontend Engineer", "years": 3,
             "highlights": ["Built a reusable component library with Storybook and Jest.",
                            "Improved Lighthouse accessibility score from 72 to 98."]},
        ],
    }
    jane = {
        "id": "C002",
        "name": "Jane Foster",
        "title": "Frontend Engineer",
        "years_experience": 2,
        "skills": ["React", "JavaScript", "CSS", "HTML", "Vue.js"],
        "education": "Self-taught / Bootcamp (General Assembly)",
        "location": "Austin, TX",
        "summary": "Frontend Engineer with 2 years of experience building "
                   "responsive web interfaces with React and Vue.",
        "experience": [
            {"company": "Glimmer", "role": "Junior Frontend Engineer", "years": 2,
             "highlights": ["Implemented responsive marketing pages in React.",
                            "Assisted in migrating styling to a shared CSS system."]},
        ],
    }
    # A strong React + 3y match for "Find me candidates with React and 3+ years".
    maria = {
        "id": "C003",
        "name": "Maria Alvarez",
        "title": "Senior Frontend Engineer",
        "years_experience": 8,
        "skills": ["React", "TypeScript", "Redux", "Next.js", "GraphQL",
                   "Jest", "Cypress", "Tailwind CSS", "Web Performance",
                   "Accessibility", "Storybook"],
        "education": "M.S. Computer Science",
        "location": "San Francisco, CA",
        "summary": "Staff-level frontend engineer with 8 years of experience "
                   "leading React + TypeScript teams and design systems.",
        "experience": [
            {"company": "Northstar", "role": "Staff Frontend Engineer", "years": 4,
             "highlights": ["Architected a micro-frontend platform serving 10M users.",
                            "Mentored 6 engineers; owned the design system."]},
            {"company": "Pinnacle", "role": "Senior Frontend Engineer", "years": 4,
             "highlights": ["Introduced end-to-end testing with Cypress.",
                            "Drove a 30% improvement in Core Web Vitals."]},
        ],
    }
    return [john, jane, maria]


def generate(n: int = 100, seed: int = 42) -> List[Dict[str, Any]]:
    """Generate ``n`` candidates deterministically."""
    rng = random.Random(seed)
    fixed = _handcrafted()
    candidates = list(fixed)
    for i in range(len(fixed) + 1, n + 1):
        candidates.append(_make_candidate(i, rng))
    return candidates


SAMPLE_JD = """\
# Senior Frontend Engineer

We are looking for a Senior Frontend Engineer to join our product team and
help build a fast, accessible, and delightful web application.

## Requirements (must have)
- 3+ years of professional frontend development experience
- Strong proficiency with React and TypeScript
- Experience with state management (Redux or similar)
- Solid understanding of HTML, CSS, and responsive design
- Experience writing unit and integration tests (Jest)

## Nice to have
- Experience with Next.js and server-side rendering
- Familiarity with GraphQL
- Knowledge of web performance optimization
- Accessibility (a11y) best practices
- Experience with a component library / design system (Storybook)

## Responsibilities
- Build and maintain user-facing features
- Collaborate closely with design and backend engineers
- Champion code quality, testing, and performance
"""


def ensure_data(n: int = 100, seed: int = 42) -> None:
    """Create the dataset on disk if it does not already exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(JD_DIR, exist_ok=True)
    if not os.path.exists(RESUMES_PATH):
        candidates = generate(n=n, seed=seed)
        with open(RESUMES_PATH, "w", encoding="utf-8") as fh:
            json.dump(candidates, fh, indent=2)
    jd_path = os.path.join(JD_DIR, "senior_frontend_engineer.md")
    if not os.path.exists(jd_path):
        with open(jd_path, "w", encoding="utf-8") as fh:
            fh.write(SAMPLE_JD)


def load_candidates() -> List[Dict[str, Any]]:
    """Load the candidate corpus, generating it first if necessary."""
    ensure_data()
    with open(RESUMES_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def render_resume(candidate: Dict[str, Any]) -> str:
    """Render a candidate dict as a plain-text resume (used by RAG + tools)."""
    lines = [
        f"{candidate['name']} — {candidate['title']}",
        f"ID: {candidate['id']} | Location: {candidate['location']} | "
        f"Experience: {candidate['years_experience']} years",
        f"Education: {candidate['education']}",
        "",
        "SUMMARY",
        candidate["summary"],
        "",
        "SKILLS",
        ", ".join(candidate["skills"]),
        "",
        "EXPERIENCE",
    ]
    for job in candidate["experience"]:
        lines.append(f"- {job['role']} @ {job['company']} ({job['years']} yr)")
        for hl in job["highlights"]:
            lines.append(f"    * {hl}")
    return "\n".join(lines)


if __name__ == "__main__":
    ensure_data()
    cands = load_candidates()
    print(f"Generated {len(cands)} candidates -> {RESUMES_PATH}")
    print("\nExample resume:\n")
    print(render_resume(cands[0]))
