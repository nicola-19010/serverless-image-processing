# Cloud Computing Project — Option 2

**Image Processing on AWS Lambda**
Course: Cloud Computing — Prof. Emiliano Casalicchio
Group: Nicolas Pacheco, Prajwal, Mathias

---

## What this project does

We deploy 3 independent AWS Lambda functions that each perform one image processing operation, evaluate their performance and scalability under different workloads, and compare deployment costs against a theoretical alternative.

| Lambda | Operation | Owner |
|---|---|---|
| `resize` | Resize image to target dimensions | Nico |
| `grayscale` | Convert to grayscale | Prajwal |
| `edge` | Edge detection | Mathias |

Each Lambda is exposed via API Gateway as a separate endpoint. Load testing is done with Locust from a local machine. Cost projection is theoretical (AWS Pricing Calculator).

---

## Repository structure

```
project/
├── README.md                  ← this file
├── requirements.txt           ← Python dependencies for local work
├── .gitignore
│
├── docs/
│   ├── WORK_PLAN.md           ← step-by-step guide for the team
│   ├── SETUP.md               ← local environment setup (Windows)
│   ├── DEPLOY.md              ← deploying to AWS Lambda
│   ├── TESTING.md             ← Postman + Locust usage
│   └── ANALYSIS.md            ← data analysis and reporting
│
├── lambdas/
│   ├── resize/
│   │   ├── lambda_function.py
│   │   ├── requirements.txt
│   │   └── test_event.json
│   ├── grayscale/             ← same structure
│   └── edge/                  ← same structure
│
├── local-tests/
│   ├── test_resize.py
│   ├── test_grayscale.py
│   ├── test_edge.py
│   ├── generate_images.py
│   └── images/
│       ├── small/    (~100 KB each)
│       ├── medium/   (~1 MB each)
│       └── large/    (~5 MB each)
│
├── postman/
│   └── CloudComputing.postman_collection.json
│
├── load-tests/
│   ├── locustfile.py
│   ├── run_scenarios.bat      ← orchestrator for all 45 scenarios
│   └── results/               ← CSV output from Locust
│
└── analysis/
    ├── analyze.ipynb          ← Jupyter notebook for charts
    └── cost_projection.py     ← 6-month cost comparison
```

---

## Where to start

1. Read `docs/WORK_PLAN.md` — the full step-by-step guide.
2. Follow `docs/SETUP.md` to get your local environment ready.
3. Pick your assigned Lambda and follow `docs/DEPLOY.md`.

---

## Quick links

- [Work plan](docs/WORK_PLAN.md)
- [Setup guide](docs/SETUP.md)
- [Deployment guide](docs/DEPLOY.md)
- [Testing guide](docs/TESTING.md)
- [Analysis guide](docs/ANALYSIS.md)
