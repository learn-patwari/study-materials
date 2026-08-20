# DSA & Algorithms — Interview Prep

> Target: 10–15 YOE · Staff / Senior Engineer
> Companies: Google, Amazon, Uber, Flipkart, Zscaler, Atlassian, JP Morgan, Goldman Sachs
> Language: Java

---

## 1. Complexity Analysis

### Q1. Big-O, amortized complexity, and common traps.

**Big-O** describes the worst-case upper bound. For interviews, always state:
1. Time complexity
2. Space complexity (including recursion stack)
3. Whether it's worst-case or average-case

**Common complexities and their triggers:**

| Complexity | Triggers |
|---|---|
| O(1) | HashMap get/put (average), array access |
| O(log n) | Binary search, BST operations, heap operations |
| O(n) | Single loop, linear scan |
| O(n log n) | Merge sort, heap sort, TreeMap operations in a loop |
| O(n²) | Nested loops without early termination |
| O(2ⁿ) | Recursive subsets, Fibonacci without memoization |
| O(n!) | Permutations |

**Amortized complexity:** The average cost per operation over a sequence of operations.
- `ArrayList.add()`: O(1) amortized (O(n) when resizing, but resize is rare)
- `Stack.push()` + full traversal: amortized O(1) per element — each element pushed/popped once

**Common traps:**
```java
// Trap 1: String concatenation in a loop — O(n²) not O(n)
String result = "";
for (String s : list) result += s; // creates new String each iteration
// Fix: StringBuilder in loop, or String.join()

// Trap 2: contains() on List is O(n) — use Set
if (list.contains(target)) { ... } // O(n) in a loop = O(n²)
Set<String> set = new HashSet<>(list);
if (set.contains(target)) { ... } // O(1)

// Trap 3: Arrays.sort() on non-primitives is O(n log n) — primitives use dual-pivot quicksort
```

---

### Q2. Space complexity in recursive algorithms.

Every recursive call uses stack space. A depth-d recursion uses O(d) stack space.

```java
// Fibonacci: O(2^n) time, O(n) space (max depth n before returning)
int fib(int n) {
    if (n <= 1) return n;
    return fib(n-1) + fib(n-2); // O(n) stack depth
}

// Tree DFS: O(h) space where h = height (O(log n) balanced, O(n) skewed)
void dfs(TreeNode node) {
    if (node == null) return;
    dfs(node.left);
    dfs(node.right);
}

// Tail recursion: Java does NOT optimize tail calls
// Always convert deep recursions to iterative if input can be large
```

---

## 2. Arrays & Strings

### Q3. Two-pointer technique — when and how.

**When:** Sorted array, finding pairs/triplets, palindrome check, removing duplicates.

```java
// Pattern 1: opposite ends — find pair with target sum in sorted array
int twoSum(int[] sorted, int target) {
    int left = 0, right = sorted.length - 1;
    while (left < right) {
        int sum = sorted[left] + sorted[right];
        if (sum == target) return true;
        else if (sum < target) left++;
        else right--;
    }
    return false;
}

// Pattern 2: same direction — remove duplicates from sorted array (in-place)
int removeDuplicates(int[] nums) {
    if (nums.length == 0) return 0;
    int slow = 0;
    for (int fast = 1; fast < nums.length; fast++) {
        if (nums[fast] != nums[slow]) {
            nums[++slow] = nums[fast]; // slow points to last unique; fast scans ahead
        }
    }
    return slow + 1;
}

// Pattern 3: container with most water (classic Google/Amazon question)
int maxArea(int[] height) {
    int left = 0, right = height.length - 1, max = 0;
    while (left < right) {
        int area = Math.min(height[left], height[right]) * (right - left);
        max = Math.max(max, area);
        if (height[left] < height[right]) left++;
        else right--;
    }
    return max;
}
```

---

### Q4. Sliding window — fixed and variable size.

**When:** Subarray/substring problems with contiguous elements, max/min/sum in window.

```java
// Fixed window: maximum sum subarray of size k
int maxSumFixed(int[] nums, int k) {
    int sum = 0;
    for (int i = 0; i < k; i++) sum += nums[i]; // initialize window
    int max = sum;
    for (int i = k; i < nums.length; i++) {
        sum += nums[i] - nums[i - k]; // slide: add right, remove left
        max = Math.max(max, sum);
    }
    return max;
}

// Variable window: longest substring with at most k distinct characters
int longestSubstringKDistinct(String s, int k) {
    Map<Character, Integer> freq = new HashMap<>();
    int left = 0, max = 0;
    for (int right = 0; right < s.length(); right++) {
        freq.merge(s.charAt(right), 1, Integer::sum); // add right char
        while (freq.size() > k) { // shrink from left until valid
            char c = s.charAt(left++);
            freq.merge(c, -1, Integer::sum);
            if (freq.get(c) == 0) freq.remove(c);
        }
        max = Math.max(max, right - left + 1);
    }
    return max;
}
```

---

### Q5. Prefix sum — range queries in O(1).

```java
// Build: O(n) once; Query: O(1) per range sum
class PrefixSum {
    private final int[] prefix;
    
    PrefixSum(int[] nums) {
        prefix = new int[nums.length + 1];
        for (int i = 0; i < nums.length; i++) {
            prefix[i + 1] = prefix[i] + nums[i];
        }
    }
    
    int rangeSum(int left, int right) { // inclusive indices
        return prefix[right + 1] - prefix[left];
    }
}

// Subarray sum equals k (count subarrays, not just check):
int subarraySum(int[] nums, int k) {
    Map<Integer, Integer> prefixCount = new HashMap<>();
    prefixCount.put(0, 1); // empty prefix
    int sum = 0, count = 0;
    for (int num : nums) {
        sum += num;
        // If (sum - k) was seen before, those subarrays sum to k
        count += prefixCount.getOrDefault(sum - k, 0);
        prefixCount.merge(sum, 1, Integer::sum);
    }
    return count;
}
```

---

## 3. Linked Lists

### Q6. Reversal, cycle detection, LRU — the canonical linked list problems.

```java
// Reverse a singly linked list — iterative
ListNode reverse(ListNode head) {
    ListNode prev = null, curr = head;
    while (curr != null) {
        ListNode next = curr.next;
        curr.next = prev;
        prev = curr;
        curr = next;
    }
    return prev;
}

// Cycle detection — Floyd's tortoise and hare
boolean hasCycle(ListNode head) {
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next;
        fast = fast.next.next;
        if (slow == fast) return true;
    }
    return false;
}

// Find cycle start:
ListNode detectCycleStart(ListNode head) {
    ListNode slow = head, fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next; fast = fast.next.next;
        if (slow == fast) {
            slow = head; // reset slow to head
            while (slow != fast) { slow = slow.next; fast = fast.next; }
            return slow; // meeting point = cycle start
        }
    }
    return null;
}

// Merge two sorted linked lists
ListNode merge(ListNode l1, ListNode l2) {
    ListNode dummy = new ListNode(0), curr = dummy;
    while (l1 != null && l2 != null) {
        if (l1.val <= l2.val) { curr.next = l1; l1 = l1.next; }
        else { curr.next = l2; l2 = l2.next; }
        curr = curr.next;
    }
    curr.next = l1 != null ? l1 : l2;
    return dummy.next;
}
```

---

### Q7. LRU Cache — the most asked LinkedHashMap/Doubly-Linked-List problem.

```java
// Approach 1: LinkedHashMap (clean, O(1) get/put)
class LRUCache extends LinkedHashMap<Integer, Integer> {
    private final int capacity;
    
    LRUCache(int capacity) {
        super(capacity, 0.75f, true); // accessOrder=true: access moves entry to end
        this.capacity = capacity;
    }
    
    public int get(int key) { return getOrDefault(key, -1); }
    
    public void put(int key, int value) { super.put(key, value); }
    
    @Override
    protected boolean removeEldestEntry(Map.Entry<Integer, Integer> eldest) {
        return size() > capacity; // auto-evict least recently used
    }
}

// Approach 2: HashMap + DoublyLinkedList (interviewer may require this)
class LRUCacheManual {
    private static class Node {
        int key, val;
        Node prev, next;
        Node(int k, int v) { key = k; val = v; }
    }
    
    private final int cap;
    private final Map<Integer, Node> map = new HashMap<>();
    private final Node head = new Node(0, 0), tail = new Node(0, 0); // sentinels
    
    LRUCacheManual(int capacity) {
        this.cap = capacity;
        head.next = tail; tail.prev = head;
    }
    
    public int get(int key) {
        if (!map.containsKey(key)) return -1;
        Node node = map.get(key);
        moveToFront(node);
        return node.val;
    }
    
    public void put(int key, int value) {
        if (map.containsKey(key)) {
            Node node = map.get(key);
            node.val = value;
            moveToFront(node);
        } else {
            Node node = new Node(key, value);
            map.put(key, node);
            addToFront(node);
            if (map.size() > cap) {
                Node lru = tail.prev;
                remove(lru);
                map.remove(lru.key);
            }
        }
    }
    
    private void addToFront(Node node) {
        node.next = head.next; node.prev = head;
        head.next.prev = node; head.next = node;
    }
    
    private void remove(Node node) {
        node.prev.next = node.next; node.next.prev = node.prev;
    }
    
    private void moveToFront(Node node) { remove(node); addToFront(node); }
}
```

---

## 4. Stacks & Queues

### Q8. Monotonic stack — the pattern for next greater/smaller element.

```java
// Next Greater Element for each array position
int[] nextGreater(int[] nums) {
    int n = nums.length;
    int[] result = new int[n];
    Arrays.fill(result, -1);
    Deque<Integer> stack = new ArrayDeque<>(); // stores indices
    
    for (int i = 0; i < n; i++) {
        // Pop all elements smaller than current — current is their answer
        while (!stack.isEmpty() && nums[stack.peek()] < nums[i]) {
            result[stack.pop()] = nums[i];
        }
        stack.push(i);
    }
    return result; // remaining in stack have no greater element → stay -1
}

// Largest Rectangle in Histogram (classic monotonic stack problem)
int largestRectangle(int[] heights) {
    Deque<Integer> stack = new ArrayDeque<>();
    int maxArea = 0;
    int[] h = Arrays.copyOf(heights, heights.length + 1); // sentinel 0 at end
    
    for (int i = 0; i < h.length; i++) {
        while (!stack.isEmpty() && h[stack.peek()] > h[i]) {
            int height = h[stack.pop()];
            int width = stack.isEmpty() ? i : i - stack.peek() - 1;
            maxArea = Math.max(maxArea, height * width);
        }
        stack.push(i);
    }
    return maxArea;
}

// Min stack — O(1) getMin()
class MinStack {
    private final Deque<int[]> stack = new ArrayDeque<>(); // [value, currentMin]
    
    void push(int val) {
        int min = stack.isEmpty() ? val : Math.min(val, stack.peek()[1]);
        stack.push(new int[]{val, min});
    }
    void pop() { stack.pop(); }
    int top() { return stack.peek()[0]; }
    int getMin() { return stack.peek()[1]; }
}
```

---

## 5. Trees

### Q9. Tree DFS patterns — inorder, preorder, postorder, path problems.

```java
// All three traversals — iterative (important for large trees avoiding stack overflow)
// Inorder (left-root-right): sorted output for BST
List<Integer> inorder(TreeNode root) {
    List<Integer> result = new ArrayList<>();
    Deque<TreeNode> stack = new ArrayDeque<>();
    TreeNode curr = root;
    while (curr != null || !stack.isEmpty()) {
        while (curr != null) { stack.push(curr); curr = curr.left; }
        curr = stack.pop();
        result.add(curr.val);
        curr = curr.right;
    }
    return result;
}

// Tree diameter (longest path between any two nodes)
int maxDiameter = 0;
int diameter(TreeNode root) {
    heightForDiameter(root);
    return maxDiameter;
}
int heightForDiameter(TreeNode node) {
    if (node == null) return 0;
    int left = heightForDiameter(node.left);
    int right = heightForDiameter(node.right);
    maxDiameter = Math.max(maxDiameter, left + right);
    return 1 + Math.max(left, right);
}

// Path sum — does a root-to-leaf path sum to target?
boolean hasPathSum(TreeNode root, int target) {
    if (root == null) return false;
    if (root.left == null && root.right == null) return root.val == target;
    return hasPathSum(root.left, target - root.val) || 
           hasPathSum(root.right, target - root.val);
}

// Lowest Common Ancestor (LCA) — O(n)
TreeNode lca(TreeNode root, TreeNode p, TreeNode q) {
    if (root == null || root == p || root == q) return root;
    TreeNode left = lca(root.left, p, q);
    TreeNode right = lca(root.right, p, q);
    return left != null && right != null ? root : (left != null ? left : right);
}
```

---

### Q10. BFS — level-order, zigzag, right view.

```java
// Level-order traversal
List<List<Integer>> levelOrder(TreeNode root) {
    List<List<Integer>> result = new ArrayList<>();
    if (root == null) return result;
    Queue<TreeNode> queue = new LinkedList<>();
    queue.offer(root);
    while (!queue.isEmpty()) {
        int size = queue.size(); // snapshot level size
        List<Integer> level = new ArrayList<>();
        for (int i = 0; i < size; i++) {
            TreeNode node = queue.poll();
            level.add(node.val);
            if (node.left != null) queue.offer(node.left);
            if (node.right != null) queue.offer(node.right);
        }
        result.add(level);
    }
    return result;
}

// Right side view (rightmost node at each level)
List<Integer> rightSideView(TreeNode root) {
    List<Integer> result = new ArrayList<>();
    if (root == null) return result;
    Queue<TreeNode> queue = new LinkedList<>();
    queue.offer(root);
    while (!queue.isEmpty()) {
        int size = queue.size();
        for (int i = 0; i < size; i++) {
            TreeNode node = queue.poll();
            if (i == size - 1) result.add(node.val); // rightmost = last in level
            if (node.left != null) queue.offer(node.left);
            if (node.right != null) queue.offer(node.right);
        }
    }
    return result;
}
```

---

### Q11. Trie — prefix search, autocomplete, word dictionary.

```java
class Trie {
    private static class TrieNode {
        TrieNode[] children = new TrieNode[26];
        boolean isEnd = false;
    }
    
    private final TrieNode root = new TrieNode();
    
    void insert(String word) {
        TrieNode curr = root;
        for (char c : word.toCharArray()) {
            int idx = c - 'a';
            if (curr.children[idx] == null) curr.children[idx] = new TrieNode();
            curr = curr.children[idx];
        }
        curr.isEnd = true;
    }
    
    boolean search(String word) {
        TrieNode node = traverse(word);
        return node != null && node.isEnd;
    }
    
    boolean startsWith(String prefix) { return traverse(prefix) != null; }
    
    // Returns all words with given prefix (autocomplete)
    List<String> autocomplete(String prefix) {
        List<String> result = new ArrayList<>();
        TrieNode node = traverse(prefix);
        if (node != null) dfsCollect(node, new StringBuilder(prefix), result);
        return result;
    }
    
    private TrieNode traverse(String s) {
        TrieNode curr = root;
        for (char c : s.toCharArray()) {
            int idx = c - 'a';
            if (curr.children[idx] == null) return null;
            curr = curr.children[idx];
        }
        return curr;
    }
    
    private void dfsCollect(TrieNode node, StringBuilder path, List<String> result) {
        if (node.isEnd) result.add(path.toString());
        for (int i = 0; i < 26; i++) {
            if (node.children[i] != null) {
                path.append((char)('a' + i));
                dfsCollect(node.children[i], path, result);
                path.deleteCharAt(path.length() - 1);
            }
        }
    }
}
```

---

## 6. Graphs

### Q12. Graph representations and BFS/DFS templates.

```java
// Adjacency list (most common in interviews)
Map<Integer, List<Integer>> graph = new HashMap<>();
graph.computeIfAbsent(0, k -> new ArrayList<>()).add(1);
graph.computeIfAbsent(1, k -> new ArrayList<>()).add(2);

// BFS template — shortest path in unweighted graph
int bfsShortestPath(Map<Integer, List<Integer>> graph, int src, int dst) {
    Queue<Integer> queue = new LinkedList<>();
    Set<Integer> visited = new HashSet<>();
    queue.offer(src); visited.add(src);
    int distance = 0;
    while (!queue.isEmpty()) {
        int size = queue.size();
        for (int i = 0; i < size; i++) {
            int node = queue.poll();
            if (node == dst) return distance;
            for (int neighbor : graph.getOrDefault(node, List.of())) {
                if (!visited.contains(neighbor)) {
                    visited.add(neighbor);
                    queue.offer(neighbor);
                }
            }
        }
        distance++;
    }
    return -1;
}

// DFS template — connected components / path existence
boolean dfs(Map<Integer, List<Integer>> graph, int node, int target, Set<Integer> visited) {
    if (node == target) return true;
    visited.add(node);
    for (int neighbor : graph.getOrDefault(node, List.of())) {
        if (!visited.contains(neighbor)) {
            if (dfs(graph, neighbor, target, visited)) return true;
        }
    }
    return false;
}
```

---

### Q13. Topological sort — Kahn's algorithm (BFS-based).

```java
// Course schedule: can you finish all courses given prerequisites?
boolean canFinish(int numCourses, int[][] prerequisites) {
    int[] inDegree = new int[numCourses];
    Map<Integer, List<Integer>> graph = new HashMap<>();
    
    for (int[] edge : prerequisites) {
        graph.computeIfAbsent(edge[1], k -> new ArrayList<>()).add(edge[0]);
        inDegree[edge[0]]++;
    }
    
    Queue<Integer> queue = new LinkedList<>();
    for (int i = 0; i < numCourses; i++) {
        if (inDegree[i] == 0) queue.offer(i);
    }
    
    int processed = 0;
    while (!queue.isEmpty()) {
        int course = queue.poll();
        processed++;
        for (int next : graph.getOrDefault(course, List.of())) {
            if (--inDegree[next] == 0) queue.offer(next);
        }
    }
    
    return processed == numCourses; // if not all processed, there's a cycle
}
```

---

### Q14. Union-Find (Disjoint Set) — connected components, cycle detection.

```java
class UnionFind {
    private final int[] parent, rank;
    private int components;
    
    UnionFind(int n) {
        parent = new int[n]; rank = new int[n];
        components = n;
        for (int i = 0; i < n; i++) parent[i] = i;
    }
    
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]); // path compression
        return parent[x];
    }
    
    boolean union(int x, int y) {
        int px = find(x), py = find(y);
        if (px == py) return false; // already connected — adding edge creates cycle
        if (rank[px] < rank[py]) { int t = px; px = py; py = t; }
        parent[py] = px;
        if (rank[px] == rank[py]) rank[px]++;
        components--;
        return true;
    }
    
    int getComponents() { return components; }
}

// Usage: number of connected components in undirected graph
int countComponents(int n, int[][] edges) {
    UnionFind uf = new UnionFind(n);
    for (int[] edge : edges) uf.union(edge[0], edge[1]);
    return uf.getComponents();
}
```

---

### Q15. Dijkstra's algorithm — shortest path in weighted graph.

```java
int[] dijkstra(int n, Map<Integer, List<int[]>> graph, int src) {
    int[] dist = new int[n];
    Arrays.fill(dist, Integer.MAX_VALUE);
    dist[src] = 0;
    
    // Min-heap: [distance, node]
    PriorityQueue<int[]> pq = new PriorityQueue<>(Comparator.comparingInt(a -> a[0]));
    pq.offer(new int[]{0, src});
    
    while (!pq.isEmpty()) {
        int[] curr = pq.poll();
        int d = curr[0], node = curr[1];
        
        if (d > dist[node]) continue; // stale entry — skip
        
        for (int[] edge : graph.getOrDefault(node, List.of())) {
            int neighbor = edge[0], weight = edge[1];
            int newDist = dist[node] + weight;
            if (newDist < dist[neighbor]) {
                dist[neighbor] = newDist;
                pq.offer(new int[]{newDist, neighbor});
            }
        }
    }
    return dist; // dist[i] = shortest distance from src to i
}
```

**Complexity:** O((V + E) log V) with a binary heap.
**Limitation:** Does not work with negative edge weights. Use Bellman-Ford for negative weights.

---

## 7. Dynamic Programming

### Q16. Memoization vs tabulation — when to use which.

**Memoization (top-down):** Recursive + HashMap cache. Write naturally; memoize later.
```java
Map<Integer, Long> memo = new HashMap<>();
long fib(int n) {
    if (n <= 1) return n;
    return memo.computeIfAbsent(n, k -> fib(k-1) + fib(k-2));
}
```

**Tabulation (bottom-up):** Iterative, fills a DP table from base cases.
```java
long fib(int n) {
    if (n <= 1) return n;
    long[] dp = new long[n + 1];
    dp[1] = 1;
    for (int i = 2; i <= n; i++) dp[i] = dp[i-1] + dp[i-2];
    return dp[n];
}
// Space-optimized: O(1) instead of O(n)
long fibOptimized(int n) {
    if (n <= 1) return n;
    long prev2 = 0, prev1 = 1;
    for (int i = 2; i <= n; i++) { long curr = prev1 + prev2; prev2 = prev1; prev1 = curr; }
    return prev1;
}
```

**Choose memoization when:** Natural recursion exists, not all states reachable, recursion tree is sparse.
**Choose tabulation when:** All states reachable, need space optimization, want to avoid recursion stack overflow.

---

### Q17. 0/1 Knapsack — the foundational DP pattern.

```java
// Can we fill a knapsack of capacity W with items of given weights/values?
int knapsack(int[] weights, int[] values, int W) {
    int n = weights.length;
    int[][] dp = new int[n + 1][W + 1];
    
    for (int i = 1; i <= n; i++) {
        for (int w = 0; w <= W; w++) {
            dp[i][w] = dp[i-1][w]; // don't take item i
            if (weights[i-1] <= w) {
                dp[i][w] = Math.max(dp[i][w], dp[i-1][w - weights[i-1]] + values[i-1]);
            }
        }
    }
    return dp[n][W];
}

// Space-optimized: O(W) instead of O(n*W)
int knapsack1D(int[] weights, int[] values, int W) {
    int[] dp = new int[W + 1];
    for (int i = 0; i < weights.length; i++) {
        for (int w = W; w >= weights[i]; w--) { // traverse right to left!
            dp[w] = Math.max(dp[w], dp[w - weights[i]] + values[i]);
        }
    }
    return dp[W];
}
```

---

### Q18. Longest Common Subsequence (LCS) and related patterns.

```java
// LCS: O(m*n) time and space
int lcs(String s, String t) {
    int m = s.length(), n = t.length();
    int[][] dp = new int[m + 1][n + 1];
    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            if (s.charAt(i-1) == t.charAt(j-1)) dp[i][j] = dp[i-1][j-1] + 1;
            else dp[i][j] = Math.max(dp[i-1][j], dp[i][j-1]);
        }
    }
    return dp[m][n];
}

// Edit Distance (Levenshtein) — same template, different recurrence
int editDistance(String s, String t) {
    int m = s.length(), n = t.length();
    int[][] dp = new int[m + 1][n + 1];
    for (int i = 0; i <= m; i++) dp[i][0] = i;
    for (int j = 0; j <= n; j++) dp[0][j] = j;
    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            if (s.charAt(i-1) == t.charAt(j-1)) dp[i][j] = dp[i-1][j-1];
            else dp[i][j] = 1 + Math.min(dp[i-1][j-1], Math.min(dp[i-1][j], dp[i][j-1]));
        }
    }
    return dp[m][n];
}

// Longest Increasing Subsequence (LIS) — O(n²) DP, O(n log n) with patience sorting
int lis(int[] nums) {
    int n = nums.length;
    int[] dp = new int[n];
    Arrays.fill(dp, 1);
    int max = 1;
    for (int i = 1; i < n; i++) {
        for (int j = 0; j < i; j++) {
            if (nums[j] < nums[i]) dp[i] = Math.max(dp[i], dp[j] + 1);
        }
        max = Math.max(max, dp[i]);
    }
    return max;
}
```

---

### Q19. Classic DP problems — coin change, house robber.

```java
// Coin change: minimum coins to make amount (unbounded knapsack variant)
int coinChange(int[] coins, int amount) {
    int[] dp = new int[amount + 1];
    Arrays.fill(dp, amount + 1); // infinity
    dp[0] = 0;
    for (int coin : coins) {
        for (int i = coin; i <= amount; i++) {
            dp[i] = Math.min(dp[i], dp[i - coin] + 1);
        }
    }
    return dp[amount] > amount ? -1 : dp[amount];
}

// House robber: max sum with no two adjacent elements
int rob(int[] nums) {
    if (nums.length == 1) return nums[0];
    int prev2 = 0, prev1 = 0;
    for (int num : nums) {
        int curr = Math.max(prev1, prev2 + num);
        prev2 = prev1;
        prev1 = curr;
    }
    return prev1;
}

// House robber II (circular): run house robber on [0..n-2] and [1..n-1], take max
int robCircular(int[] nums) {
    if (nums.length == 1) return nums[0];
    return Math.max(
        robRange(nums, 0, nums.length - 2),
        robRange(nums, 1, nums.length - 1)
    );
}
int robRange(int[] nums, int start, int end) {
    int prev2 = 0, prev1 = 0;
    for (int i = start; i <= end; i++) {
        int curr = Math.max(prev1, prev2 + nums[i]);
        prev2 = prev1; prev1 = curr;
    }
    return prev1;
}

// Maximum subarray (Kadane's algorithm) — O(n), O(1)
int maxSubarray(int[] nums) {
    int maxSum = nums[0], currSum = nums[0];
    for (int i = 1; i < nums.length; i++) {
        currSum = Math.max(nums[i], currSum + nums[i]);
        maxSum = Math.max(maxSum, currSum);
    }
    return maxSum;
}
```

---

## 8. Heap & Priority Queue

### Q20. K-th largest/smallest element — classic heap problems.

```java
// K-th largest: min-heap of size k — top = k-th largest
int findKthLargest(int[] nums, int k) {
    PriorityQueue<Integer> minHeap = new PriorityQueue<>();
    for (int num : nums) {
        minHeap.offer(num);
        if (minHeap.size() > k) minHeap.poll(); // evict smallest
    }
    return minHeap.peek(); // top of min-heap = k-th largest
}

// Merge K sorted lists using a min-heap
ListNode mergeKLists(ListNode[] lists) {
    PriorityQueue<ListNode> pq = new PriorityQueue<>(Comparator.comparingInt(n -> n.val));
    for (ListNode head : lists) if (head != null) pq.offer(head);
    
    ListNode dummy = new ListNode(0), curr = dummy;
    while (!pq.isEmpty()) {
        ListNode node = pq.poll();
        curr.next = node;
        curr = curr.next;
        if (node.next != null) pq.offer(node.next);
    }
    return dummy.next;
}

// Top K frequent elements
List<Integer> topKFrequent(int[] nums, int k) {
    Map<Integer, Integer> freq = new HashMap<>();
    for (int num : nums) freq.merge(num, 1, Integer::sum);
    
    // Min-heap by frequency, size k
    PriorityQueue<Map.Entry<Integer, Integer>> pq = 
        new PriorityQueue<>(Comparator.comparingInt(Map.Entry::getValue));
    
    for (Map.Entry<Integer, Integer> entry : freq.entrySet()) {
        pq.offer(entry);
        if (pq.size() > k) pq.poll();
    }
    
    return pq.stream().map(Map.Entry::getKey).collect(Collectors.toList());
}
```

---

## 9. Sorting

### Q21. Key sorting algorithms — when does each algorithm win?

```java
// Merge Sort — O(n log n) guaranteed, stable, O(n) extra space
void mergeSort(int[] arr, int left, int right) {
    if (left >= right) return;
    int mid = left + (right - left) / 2;
    mergeSort(arr, left, mid);
    mergeSort(arr, mid + 1, right);
    mergeSorted(arr, left, mid, right);
}

void mergeSorted(int[] arr, int left, int mid, int right) {
    int[] temp = Arrays.copyOfRange(arr, left, right + 1);
    int i = 0, j = mid - left + 1, k = left;
    while (i <= mid - left && j < temp.length) {
        arr[k++] = temp[i] <= temp[j] ? temp[i++] : temp[j++];
    }
    while (i <= mid - left) arr[k++] = temp[i++];
    while (j < temp.length) arr[k++] = temp[j++];
}

// QuickSelect — O(n) average for K-th element (Lomuto partition)
int quickSelect(int[] nums, int left, int right, int k) {
    if (left == right) return nums[left];
    int pivot = partition(nums, left, right);
    if (pivot == k) return nums[k];
    else if (pivot < k) return quickSelect(nums, pivot + 1, right, k);
    else return quickSelect(nums, left, pivot - 1, k);
}

int partition(int[] nums, int left, int right) {
    int pivot = nums[right], i = left;
    for (int j = left; j < right; j++) {
        if (nums[j] <= pivot) { int t = nums[i]; nums[i] = nums[j]; nums[j] = t; i++; }
    }
    int t = nums[i]; nums[i] = nums[right]; nums[right] = t;
    return i;
}
```

**When to use:**
- Merge sort: stable sort needed, linked lists (no random access), guaranteed O(n log n)
- Quick sort: average O(n log n), in-place, cache-friendly — Java uses dual-pivot quicksort for primitives
- Counting sort: O(n+k) when range k is small (sorting ages, ratings)
- Heap sort: O(n log n) guaranteed, O(1) extra space — but poor cache performance

---

## 10. Company-Tagged Patterns

### Q22. Google — BFS/DFS on implicit graphs, sliding window.

Common Google patterns:
```java
// Word ladder (BFS on implicit graph — each word is a node)
int ladderLength(String beginWord, String endWord, List<String> wordList) {
    Set<String> wordSet = new HashSet<>(wordList);
    if (!wordSet.contains(endWord)) return 0;
    
    Queue<String> queue = new LinkedList<>();
    queue.offer(beginWord);
    Set<String> visited = new HashSet<>();
    visited.add(beginWord);
    int steps = 1;
    
    while (!queue.isEmpty()) {
        int size = queue.size();
        for (int i = 0; i < size; i++) {
            String word = queue.poll();
            char[] chars = word.toCharArray();
            for (int j = 0; j < chars.length; j++) {
                char orig = chars[j];
                for (char c = 'a'; c <= 'z'; c++) {
                    chars[j] = c;
                    String next = new String(chars);
                    if (next.equals(endWord)) return steps + 1;
                    if (wordSet.contains(next) && !visited.contains(next)) {
                        visited.add(next);
                        queue.offer(next);
                    }
                }
                chars[j] = orig;
            }
        }
        steps++;
    }
    return 0;
}
```

---

### Q23. Amazon — tree problems, design questions.

```java
// Serialize and deserialize binary tree (classic Amazon)
class Codec {
    private static final String NULL = "#", SEP = ",";
    
    String serialize(TreeNode root) {
        StringBuilder sb = new StringBuilder();
        serializeHelper(root, sb);
        return sb.toString();
    }
    
    private void serializeHelper(TreeNode node, StringBuilder sb) {
        if (node == null) { sb.append(NULL).append(SEP); return; }
        sb.append(node.val).append(SEP);
        serializeHelper(node.left, sb);
        serializeHelper(node.right, sb);
    }
    
    TreeNode deserialize(String data) {
        Queue<String> queue = new LinkedList<>(Arrays.asList(data.split(SEP)));
        return deserializeHelper(queue);
    }
    
    private TreeNode deserializeHelper(Queue<String> q) {
        String val = q.poll();
        if (NULL.equals(val)) return null;
        TreeNode node = new TreeNode(Integer.parseInt(val));
        node.left = deserializeHelper(q);
        node.right = deserializeHelper(q);
        return node;
    }
}
```

---

### Q24. Zscaler patterns — from `DSA-Interview-Experiences.md`.

Based on reported Zscaler interview patterns:

**Frequently asked:**
1. **Intervals** — merge overlapping intervals, insert interval, meeting rooms
2. **Sliding window** — longest substring without repeating characters, minimum window substring
3. **Trees** — validate BST, kth smallest in BST
4. **System design over code** — often asked at L5+ to design rate limiter, cache system

```java
// Merge intervals (Zscaler reported)
int[][] mergeIntervals(int[][] intervals) {
    Arrays.sort(intervals, Comparator.comparingInt(a -> a[0]));
    List<int[]> result = new ArrayList<>();
    int[] curr = intervals[0];
    for (int i = 1; i < intervals.length; i++) {
        if (intervals[i][0] <= curr[1]) {
            curr[1] = Math.max(curr[1], intervals[i][1]);
        } else {
            result.add(curr);
            curr = intervals[i];
        }
    }
    result.add(curr);
    return result.toArray(new int[0][]);
}

// Minimum window substring (Zscaler/Google pattern)
String minWindowSubstring(String s, String t) {
    Map<Character, Integer> need = new HashMap<>();
    for (char c : t.toCharArray()) need.merge(c, 1, Integer::sum);
    
    int left = 0, have = 0, required = need.size();
    int[] best = {-1, 0, 0}; // [length, left, right]
    Map<Character, Integer> window = new HashMap<>();
    
    for (int right = 0; right < s.length(); right++) {
        char c = s.charAt(right);
        window.merge(c, 1, Integer::sum);
        if (need.containsKey(c) && window.get(c).equals(need.get(c))) have++;
        
        while (have == required) {
            if (best[0] == -1 || right - left + 1 < best[0]) {
                best[0] = right - left + 1; best[1] = left; best[2] = right;
            }
            char removed = s.charAt(left++);
            window.merge(removed, -1, Integer::sum);
            if (need.containsKey(removed) && window.get(removed) < need.get(removed)) have--;
        }
    }
    return best[0] == -1 ? "" : s.substring(best[1], best[2] + 1);
}
```

---

## 11. Backtracking

### Q25. Backtracking template — subsets, permutations, combinations.

```java
// Subsets — power set
List<List<Integer>> subsets(int[] nums) {
    List<List<Integer>> result = new ArrayList<>();
    backtrack(nums, 0, new ArrayList<>(), result);
    return result;
}

void backtrack(int[] nums, int start, List<Integer> current, List<List<Integer>> result) {
    result.add(new ArrayList<>(current)); // add current subset
    for (int i = start; i < nums.length; i++) {
        current.add(nums[i]);            // choose
        backtrack(nums, i + 1, current, result); // explore
        current.remove(current.size() - 1);       // unchoose
    }
}

// Permutations
List<List<Integer>> permutations(int[] nums) {
    List<List<Integer>> result = new ArrayList<>();
    permuteHelper(nums, new boolean[nums.length], new ArrayList<>(), result);
    return result;
}

void permuteHelper(int[] nums, boolean[] used, List<Integer> current, List<List<Integer>> result) {
    if (current.size() == nums.length) { result.add(new ArrayList<>(current)); return; }
    for (int i = 0; i < nums.length; i++) {
        if (used[i]) continue;
        used[i] = true;
        current.add(nums[i]);
        permuteHelper(nums, used, current, result);
        current.remove(current.size() - 1);
        used[i] = false;
    }
}

// N-Queens — classic backtracking
List<List<String>> solveNQueens(int n) {
    List<List<String>> result = new ArrayList<>();
    int[] queens = new int[n]; // queens[i] = column of queen in row i
    Arrays.fill(queens, -1);
    Set<Integer> cols = new HashSet<>(), diag1 = new HashSet<>(), diag2 = new HashSet<>();
    nQueensBacktrack(0, n, queens, cols, diag1, diag2, result);
    return result;
}

void nQueensBacktrack(int row, int n, int[] queens, Set<Integer> cols,
                      Set<Integer> diag1, Set<Integer> diag2, List<List<String>> result) {
    if (row == n) { result.add(buildBoard(queens, n)); return; }
    for (int col = 0; col < n; col++) {
        if (cols.contains(col) || diag1.contains(row - col) || diag2.contains(row + col)) continue;
        queens[row] = col; cols.add(col); diag1.add(row - col); diag2.add(row + col);
        nQueensBacktrack(row + 1, n, queens, cols, diag1, diag2, result);
        queens[row] = -1; cols.remove(col); diag1.remove(row - col); diag2.remove(row + col);
    }
}
```

---

## 12. Interview Strategy

### Q26. Approach to any DSA problem in an interview.

**Framework (4 minutes before coding):**
```
1. Clarify: input constraints, edge cases, expected output format
   - "Can the array be empty? Sorted? Negative numbers?"
   - "What if there are duplicates?"

2. Brute force first: state it aloud even if you know a better approach
   - "Naive: O(n²) — try all pairs. Better: sort first + two-pointer O(n log n)."

3. Identify the pattern:
   - Contiguous subarray → sliding window or prefix sum
   - K-th element → heap
   - Sorted input or optimal substructure → binary search or DP
   - Graph/reachability → BFS/DFS
   - All combinations/paths → backtracking

4. Complexity before coding: state time AND space
   - "O(n log n) time, O(n) space for the prefix map"

5. Code in steps: start with the happy path, handle edge cases after
```

**When stuck:**
- "Can I solve it with extra space?" → usually reveals a HashMap/Set approach
- "What if I sort it?" → often enables two-pointer or binary search
- "Can I decompose: define what dp[i] means?" → DP becomes clearer

---

*Total: 26 Q&As across 12 sections.*
*Key patterns by company: Google (BFS implicit graphs, divide & conquer), Amazon (trees, design), Uber (graphs, intervals), Goldman Sachs (DP, heaps), Zscaler (intervals, sliding window, BST).*
