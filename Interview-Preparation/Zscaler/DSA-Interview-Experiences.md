[← Back to Zscaler folder](README.md)

# Zscaler — DSA Interview Experiences & Prep

> **What this is:** a study list of the **actual DSA topics and problems reported** by
> candidates who interviewed at Zscaler (Glassdoor, LeetCode Discuss, GeeksforGeeks, Medium,
> etc.), organized into a practice plan. Use it to focus your DSA prep on what Zscaler actually
> asks.
>
> ⚠️ **Reality check:** these are *community-reported* experiences (mostly campus / OA / SDE-1 /
> Senior SWE, with fewer Staff-level data points). Treat them as **strong signal on patterns**,
> not a guaranteed question bank. Difficulty is medium→hard; Glassdoor rates the process ~3.2/5
> difficulty, ~15 days. Sources are listed at the bottom.

---

## The reported interview shape

| Stage | What's reported |
|-------|-----------------|
| **Online Assessment (HackerRank)** | ~3 coding problems (medium→hard) + MCQs on CS fundamentals (**networking, OS**). Some report 20 MCQ + 3 DSA (2 easy, 1 medium). ~90 min. Need ~2/3 clean to advance. |
| **Coding / DSA rounds** | 1–2 problems live; start with basics, difficulty ramps; interviewer probes optimization & complexity. |
| **System design** | Cloud-native focus (see [Round 4](Sr-Staff-SDE-Unified-API-Platform/Round-4-Architecture-Design.md)). |
| **Networking + Linux deep-dive** | Given Zscaler's domain; more relevant for infra/C-C++ roles. |
| **Managerial / HM** | Projects, resume, scenario-based. |

> 💡 **Zscaler-specific tilt:** **interval problems** show up a lot (they map naturally to network
> traffic timestamps), and **bit manipulation** surfaces more than at most companies. Don't skip
> those two.

---

## Named problems candidates reported (drill these first)

These specific problems were called out in reports:

| Problem | Pattern | LeetCode ref |
|---------|---------|--------------|
| **Min Stack** (design a stack with O(1) getMin) | Stack design | LC 155 |
| **Merge Intervals** | Intervals | LC 56 |
| **Shortest Path in Binary Matrix** | Graph / BFS on grid | LC 1091 |
| **Maximum Strong Pair XOR** | Bit manipulation / Trie | LC 2932/2935 |
| **Largest Number After Digit Swaps by Parity** | Greedy / sorting | LC 2231 |
| Tree-based problem (reported OA) | Trees | — |
| 2D matrix problem (reported OA) | Matrix traversal | — |
| **Custom `malloc`/`free`** (C/C++ roles) | Systems / memory mgmt | — |

Also repeatedly cited *categories*: implement using **HashMaps**, **Trie**, **Greedy with
Heaps**, and **DP based on LIS (Longest Increasing Subsequence)**.

---

## Priority patterns → curated practice set

Practice in this order (highest reported frequency first). Aim for ~3–5 problems per pattern.

### 1. Intervals ⭐ (Zscaler favorite)
- Merge Intervals (LC 56), Insert Interval (57), Non-overlapping Intervals (435),
  Meeting Rooms II (253), Interval List Intersections (986).

### 2. Stacks & Design
- Min Stack (155), Valid Parentheses (20), Daily Temperatures (739),
  Largest Rectangle in Histogram (84), Implement Queue using Stacks (232).

### 3. Graphs / BFS-DFS / Grids ⭐
- Shortest Path in Binary Matrix (1091), Number of Islands (200), Rotting Oranges (994),
  Course Schedule I/II (207/210 — topo sort), Clone Graph (133), Word Ladder (127).

### 4. Bit Manipulation ⭐ (surfaces more than expected)
- Single Number (136), Number of 1 Bits (191), Counting Bits (338),
  Maximum XOR of Two Numbers (421 — Trie of bits), Maximum Strong Pair XOR (2932).

### 5. HashMap / Hashing
- Two Sum (1), Group Anagrams (49), Subarray Sum Equals K (560),
  Longest Consecutive Sequence (128), Top K Frequent Elements (347).

### 6. Trie
- Implement Trie (208), Word Search II (212), Replace Words (648),
  Maximum XOR (421) — bit-trie crossover.

### 7. Heap / Priority Queue (incl. "Greedy with Heaps")
- Kth Largest (215), Merge K Sorted Lists (23), Task Scheduler (621),
  Find Median from Data Stream (295), Reorganize String (767).

### 8. Dynamic Programming (esp. LIS family)
- Longest Increasing Subsequence (300), Russian Doll Envelopes (354),
  Maximum Subarray (53), Coin Change (322), House Robber (198), Edit Distance (72).

### 9. Strings / Two Pointers / Sliding Window
- Longest Substring Without Repeating Chars (3), Minimum Window Substring (76),
  3Sum (15), Longest Palindromic Substring (5), String to Integer/atoi (8).

### 10. Design (data-structure) — overlaps machine coding
- LRU Cache (146), LFU Cache (460), Design HashMap (706),
  Time Based Key-Value Store (981), Insert Delete GetRandom O(1) (380).

> 💡 **Best ROI given your target role (API platform):** intervals, LRU/LFU cache, Trie routing,
> heaps/top-K, topological sort, and sliding-window rate limiting — these double as
> [machine-coding](Sr-Staff-SDE-Unified-API-Platform/Round-3-Coding-and-Machine-Coding.md)
> building blocks.

---

## MCQ / fundamentals to review (OA)

The HackerRank MCQs lean on **computer networking** and **OS**:
- Networking: TCP vs UDP, TCP handshake, HTTP/HTTPS, TLS, DNS, subnetting, OSI layers, routing —
  *especially relevant given Zscaler's domain.*
- OS: processes vs threads, scheduling, deadlocks, memory management, paging, concurrency.
- DBMS basics, time/space complexity.

---

## A 2-week DSA drill plan

- **Days 1–3:** Intervals + Stacks (the two most-cited early patterns) — ~5 problems/day.
- **Days 4–6:** Graphs/grids + Topological sort.
- **Days 7–8:** Bit manipulation + Trie (the Zscaler "surprise" area).
- **Days 9–10:** Heaps/Top-K + HashMap patterns.
- **Days 11–12:** DP (LIS family) + Strings/sliding window.
- **Days 13–14:** Design DS (LRU/LFU/TimeMap) + timed mixed mock (mimic the 90-min OA: 3 problems).
- **Throughout:** 15 min/day of networking + OS MCQs.

**How to practice (Staff-level signal):** always state brute force → bottleneck → optimized
approach → complexity → edge cases, and narrate. Then ask yourself "how would this scale to a
distributed system?" — that's the bridge Zscaler interviewers like.

---

## Sources (community-reported experiences)

- [Glassdoor — Zscaler Interview Questions](https://www.glassdoor.co.in/Interview/Zscaler-Interview-Questions-E359434.htm)
- [Glassdoor — Zscaler Senior Software Engineer](https://www.glassdoor.co.in/Interview/Zscaler-Senior-Software-Engineer-Interview-Questions-EI_IE359434.0,7_KO8,32.htm)
- [LeetCode Discuss — Zscaler Senior Software Engineer, Bangalore](https://leetcode.com/discuss/interview-experience/2174357/zscaler-senior-software-engineer-bangalore-awaited)
- [GeeksforGeeks — Zscaler Interview Experience](https://www.geeksforgeeks.org/interview-experiences/zscaler-interview-experience/)
- [Dataford — Zscaler Software Engineer Guide](https://dataford.io/interview-guides/zscaler/software-engineer)
- [Medium — Anvesha Jain: My Interview Experience at Zscaler](https://medium.com/@iamanveshajain/my-interview-experience-at-zscaler-a-deep-dive-into-technical-problem-solving-18d98317e06a)
- [Medium — adarshpy: Zscaler ASE Interview Experience](https://medium.com/@adarshpy/zscaler-associate-software-engineer-interview-experience-9e1d3bbfe28a)
- [InterviewQuery — Zscaler Software Engineer Guide](https://www.interviewquery.com/interview-guides/zscaler-software-engineer)

> 📌 These skew toward campus/OA/SDE-1 and Senior SWE reports; **Staff-level loops are lighter on
> raw DSA and heavier on design** — so weight your time toward
> [Round 4 (architecture)](Sr-Staff-SDE-Unified-API-Platform/Round-4-Architecture-Design.md) and
> [Round 3 (machine coding)](Sr-Staff-SDE-Unified-API-Platform/Round-3-Coding-and-Machine-Coding.md),
> while keeping these DSA patterns sharp for the coding round.
