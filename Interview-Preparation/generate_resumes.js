/**
 * Resume Generator — JOBS_PIPELINE
 *
 * Each entry drives a tailored resume via build_all.py + Microsoft Word COM.
 * Focus variants:
 *   JAVA_IAM      — Keycloak, OAuth 2.0, SAML, SSO, multi-tenant auth
 *   MLOPS         — Kubeflow, LangChain, drift detection, Kafka pipelines
 *   JAVA_AGENTIC  — LangGraph, RAG, multi-agent orchestration, GenAI
 *   JAVA_BACKEND  — Spring Boot 3, microservices, Kafka, Kubernetes
 *   JAVA_AI       — balances Java backend with AI/LLM integration
 *
 * Sorted by matchScore descending.
 * NEVER fabricate experience or achievements.
 * NEVER modify existing entries — only append new ones.
 */

const JOBS_PIPELINE = [
  // ── Run 1 · 2026-07-24 ────────────────────────────────────────────────────

  {
    company:    'WellsFargo',
    role:       'Senior Software Engineer – Java, Spring Boot, Kafka',
    fileSlug:   'WellsFargo_SSE_Java_Kafka',
    matchScore: 91,
    atsScore:   92,
    applyLink:  'https://www.wellsfargojobs.com/en/jobs/r-542852/senior-software-engineer-java-spring-boot-kafka/',
    focus:      'JAVA_BACKEND',
    keywords:   ['Java', 'Spring Boot', 'Apache Kafka', 'Microservices', 'REST APIs',
                 'Kubernetes', 'CI/CD', 'Jenkins', 'Redis', 'SQL Server', 'Oracle',
                 'cloud-native', 'stateless services', 'resilience']
  },

  {
    company:    'WellsFargo',
    role:       'Senior Software Engineer – Java Full Stack',
    fileSlug:   'WellsFargo_SSE_FullStack',
    matchScore: 88,
    atsScore:   90,
    applyLink:  'https://www.wellsfargojobs.com/en/jobs/r-545076/senior-software-engineer-java-full-stack/',
    focus:      'JAVA_BACKEND',
    keywords:   ['Java', 'Spring Boot', 'Microservices', 'Kafka', 'Redis',
                 'REST API', 'technical mentorship', 'code review', 'scalability']
  },

  {
    company:    'BlueYonder',
    role:       'Senior Software Engineer – Java, Springboot, Microservices, Kafka, MongoDB',
    fileSlug:   'BlueYonder_SSE_Java_Kafka',
    matchScore: 88,
    atsScore:   90,
    applyLink:  'https://in.linkedin.com/jobs/view/senior-software-engineer-java-springboot-microservices-kafka-mongodb-at-blue-yonder-3731842813',
    focus:      'JAVA_BACKEND',
    keywords:   ['Java', 'Spring Boot', 'Microservices', 'Apache Kafka', 'MongoDB',
                 'Hibernate', 'REST API', 'SQL', 'distributed systems']
  },

  {
    company:    'Infosys',
    role:       'MLOps Engineer',
    fileSlug:   'Infosys_MLOps_Engineer',
    matchScore: 88,
    atsScore:   91,
    applyLink:  'https://in.linkedin.com/jobs/view/mlops-engineer-at-infosys-4417863340',
    focus:      'MLOPS',
    keywords:   ['MLOps', 'Kubeflow', 'Kubernetes', 'Docker', 'CI/CD',
                 'MLflow', 'model lifecycle', 'drift detection', 'model deployment',
                 'model monitoring', 'retraining', 'Kafka', 'Python']
  },

  {
    company:    'Deloitte',
    role:       'Senior Consultant – Full Stack Engineering',
    fileSlug:   'Deloitte_SC_FullStack',
    matchScore: 87,
    atsScore:   90,
    applyLink:  'https://southasiacareers.deloitte.com/job/Bengaluru-Senior-Consultant-Full-Stack-Bengaluru-Engineering-Platform-Development-&-Integration/58011844/',
    focus:      'JAVA_BACKEND',
    keywords:   ['Java', 'Spring Boot', 'REST API', 'Microservices', 'Angular',
                 'SQL', 'Git', 'OOPs', 'Agile', 'CI/CD', 'scalable applications']
  },

  {
    company:    'WellsFargo',
    role:       'Senior Software Engineer – Full Stack Java, Spring Boot, ReactJS, AI',
    fileSlug:   'WellsFargo_SSE_FullStack_AI',
    matchScore: 85,
    atsScore:   88,
    applyLink:  'https://www.wellsfargojobs.com/en/jobs/r-538240/senior-software-engineer-full-stack-java-spring-boot-reactjs-ai/',
    focus:      'JAVA_AI',
    keywords:   ['Java', 'Spring Boot', 'ReactJS', 'AI', 'Microservices',
                 'Spring JPA', 'REST API', 'GenAI', 'LLM integration']
  },

  {
    company:    'Cognizant',
    role:       'AI Engineer – Python, LangChain, LangGraph, Agentic AI, LLMs',
    fileSlug:   'Cognizant_AI_Engineer_Agentic',
    matchScore: 83,
    atsScore:   85,
    applyLink:  'https://careers.cognizant.com/india-en/jobs/00068075031/ai-engineer-python-langchain-langgraph-agentic-ai-api-llms/',
    focus:      'JAVA_AGENTIC',
    keywords:   ['Python', 'LangChain', 'LangGraph', 'Agentic AI', 'RAG',
                 'multi-agent orchestration', 'LLMs', 'FastAPI', 'PostgreSQL',
                 'autonomous agents', 'planning', 'reasoning', 'tool-use']
  },

  {
    company:    'Wabtec',
    role:       'MLOps Engineer',
    fileSlug:   'Wabtec_MLOps_Engineer',
    matchScore: 80,
    atsScore:   82,
    applyLink:  'https://careers.wabtec.com/job/mlops-engineer-in-bengaluru-ka-india-jid-1236',
    focus:      'MLOPS',
    keywords:   ['MLOps', 'Kubernetes', 'Docker', 'CI/CD', 'model deployment',
                 'model monitoring', 'pipeline automation', 'Python']
  },

  // ── Run 2 · 2026-08-06 ────────────────────────────────────────────────────

  {
    company:    'Cognizant',
    role:       'Senior Backend Java Engineer – Microservices & Kafka',
    fileSlug:   'Cognizant_SSE_Java_Kafka',
    matchScore: 88,
    atsScore:   90,
    applyLink:  'https://www.linkedin.com/jobs/view/senior-backend-java-engineer-microservices-kafka-at-cognizant-4428002527',
    focus:      'JAVA_BACKEND',
    keywords:   ['Java', 'Spring Boot', 'Apache Kafka', 'Microservices', 'REST APIs',
                 'JUnit5', 'distributed systems', 'event-driven', 'consumer groups',
                 'SQL', 'multithreading', 'scalable backend', 'production-grade services']
  },

  {
    company:    'UST',
    role:       'Senior Java Backend Lead – Kafka & Microservices',
    fileSlug:   'UST_Lead_Java_Kafka',
    matchScore: 85,
    atsScore:   88,
    applyLink:  'https://in.linkedin.com/jobs/view/senior-java-backend-lead-%E2%80%93-kafka-microservices-7-yoe-any-ust-location-immediate-joiner-at-ust-4392190440',
    focus:      'JAVA_BACKEND',
    keywords:   ['Java', 'Spring Boot', 'Apache Kafka', 'Microservices', 'REST APIs',
                 'multithreading', 'concurrency', 'design patterns', 'SQL', 'Git',
                 'unit testing', 'Docker', 'Kubernetes', 'Spring Cloud']
  },

  {
    company:    'UKG',
    role:       'Staff Software Engineer – Cloud & Kubernetes',
    fileSlug:   'UKG_Staff_Cloud_Kubernetes',
    matchScore: 82,
    atsScore:   85,
    applyLink:  'https://www.linkedin.com/jobs/view/staff-software-engineer-cloud-kubernetes-at-ukg-4444262228',
    focus:      'JAVA_BACKEND',
    keywords:   ['Kubernetes', 'containers', 'Kafka', 'Redis', 'event-driven systems',
                 'distributed caching', 'observability', 'Grafana', 'OpenTelemetry',
                 'Spring Boot', 'microservices', 'CI/CD', 'cloud-native']
  },
];

module.exports = { JOBS_PIPELINE };
