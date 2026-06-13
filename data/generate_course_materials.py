"""
data/generate_course_materials.py
Generates a rich synthetic knowledge base for CSAI 230 — Data Structures.
Run once: python -m data.generate_course_materials
"""
import json
import os

MATERIALS_PATH = os.path.join(os.path.dirname(__file__), "course_materials.json")

COURSE_MATERIALS = [
    # ── Arrays ────────────────────────────────────────────────────────────────
    {
        "id": "arrays_intro",
        "topic": "Arrays",
        "type": "concept",
        "title": "Introduction to Arrays",
        "content": (
            "An array is a contiguous block of memory that stores elements of the same type. "
            "Elements are accessed by index in O(1) time. Arrays have fixed size in most low-level "
            "languages (C, Java primitives), though Python lists are dynamic arrays internally. "
            "A static array of size n occupies n × sizeof(element) bytes. Indexing starts at 0 in "
            "most languages. Arrays provide cache-friendly access because elements are stored "
            "sequentially in memory — a major performance advantage over linked structures."
        ),
    },
    {
        "id": "arrays_operations",
        "topic": "Arrays",
        "type": "operations",
        "title": "Array Time Complexities",
        "content": (
            "Access by index: O(1). Search (unsorted): O(n). Search (sorted, binary): O(log n). "
            "Insertion at end: O(1) amortized for dynamic arrays (O(n) worst case on resize). "
            "Insertion at arbitrary position: O(n) — requires shifting elements. "
            "Deletion at end: O(1). Deletion at arbitrary position: O(n). "
            "Space complexity: O(n). Dynamic arrays (like Python list or Java ArrayList) double "
            "their capacity when full, giving amortized O(1) append."
        ),
    },
    {
        "id": "arrays_misconceptions",
        "topic": "Arrays",
        "type": "misconceptions",
        "title": "Common Array Misconceptions",
        "content": (
            "Misconception 1: Arrays are always faster than linked lists. Truth: Arrays are faster "
            "for random access (O(1) vs O(n)) but slower for frequent insertions/deletions in the "
            "middle. Misconception 2: arr[-1] gives undefined behavior everywhere. In Python, "
            "negative indices wrap around (arr[-1] is the last element). In C, it is undefined "
            "behavior. Misconception 3: 'length' and 'capacity' are the same. In dynamic arrays, "
            "capacity is the allocated memory; length is how many elements are stored. "
            "Misconception 4: Appending to a Python list is always O(1). It is O(1) amortized, "
            "but individual appends may trigger O(n) resizing."
        ),
    },
    {
        "id": "arrays_worked_example",
        "topic": "Arrays",
        "type": "worked_example",
        "title": "Two-Sum Problem Walkthrough",
        "content": (
            "Problem: Given an array nums and a target, return indices of two numbers that add to target. "
            "Brute force O(n²): two nested loops checking every pair. "
            "Optimized O(n) using a hash map: iterate once; for each element x, check if (target - x) "
            "is in the map. If yes, return the stored index and current index. If no, store x → index. "
            "Example: nums=[2,7,11,15], target=9. Iteration 1: x=2, need 7, not in map → store {2:0}. "
            "Iteration 2: x=7, need 2, found at index 0 → return [0,1]. "
            "This trades O(n) space for O(n) time improvement."
        ),
    },

    # ── Linked Lists ──────────────────────────────────────────────────────────
    {
        "id": "linked_list_intro",
        "topic": "Linked Lists",
        "type": "concept",
        "title": "Singly and Doubly Linked Lists",
        "content": (
            "A linked list is a sequence of nodes where each node holds a value and a pointer to "
            "the next node (singly linked) or both next and previous nodes (doubly linked). "
            "Unlike arrays, nodes need not be contiguous in memory. The head pointer points to the "
            "first node; the tail's next pointer is None. A doubly linked list additionally stores "
            "a prev pointer, enabling O(1) deletion when you have a reference to the node. "
            "Linked lists excel at frequent insertions/deletions at known positions but have O(n) "
            "random access because traversal must start from the head."
        ),
    },
    {
        "id": "linked_list_operations",
        "topic": "Linked Lists",
        "type": "operations",
        "title": "Linked List Complexities and Patterns",
        "content": (
            "Access by index: O(n). Search: O(n). Insertion at head: O(1). Insertion at tail "
            "(with tail pointer): O(1); without tail pointer: O(n). Insertion at arbitrary "
            "position (given node reference): O(1); finding position first: O(n). "
            "Deletion at head: O(1). Deletion at tail (doubly linked): O(1); singly linked: O(n). "
            "Common patterns: Floyd's cycle detection (fast/slow pointers), reversing a list "
            "in-place using three pointers (prev, curr, next), finding the middle node using "
            "fast/slow pointers where fast moves 2× speed."
        ),
    },
    {
        "id": "linked_list_misconceptions",
        "topic": "Linked Lists",
        "type": "misconceptions",
        "title": "Common Linked List Misconceptions",
        "content": (
            "Misconception 1: Linked lists always use less memory than arrays. Truth: each node "
            "stores a pointer (8 bytes on 64-bit systems), so a linked list of integers uses more "
            "memory than an array. Misconception 2: You can delete a node in O(1) in a singly "
            "linked list without knowing the previous node. You cannot — you must traverse to find "
            "prev, making it O(n) unless given the predecessor. Misconception 3: A circular linked "
            "list always has a cycle bug. Circular lists are intentional data structures used in "
            "round-robin scheduling; Floyd's algorithm detects unintentional cycles."
        ),
    },

    # ── Stacks & Queues ───────────────────────────────────────────────────────
    {
        "id": "stack_intro",
        "topic": "Stacks",
        "type": "concept",
        "title": "Stack — LIFO Abstract Data Type",
        "content": (
            "A stack is a Last-In-First-Out (LIFO) abstract data type. The two core operations are "
            "push (add to top) and pop (remove from top), both O(1). peek/top returns the top "
            "element without removing it. Stacks are used for: function call management (call stack), "
            "expression parsing and evaluation (shunting-yard algorithm), undo/redo functionality, "
            "DFS (depth-first search) iterative implementation, and balanced parentheses checking. "
            "Implementation: use a Python list (append = push, pop = pop), or a deque from "
            "collections module for thread safety."
        ),
    },
    {
        "id": "queue_intro",
        "topic": "Queues",
        "type": "concept",
        "title": "Queue — FIFO Abstract Data Type",
        "content": (
            "A queue is a First-In-First-Out (FIFO) abstract data type. enqueue adds to the rear; "
            "dequeue removes from the front — both O(1) with correct implementation. "
            "Use collections.deque in Python for O(1) operations at both ends (list.pop(0) is O(n)). "
            "Variants: deque (double-ended queue), priority queue (heap-based, O(log n) operations), "
            "circular queue (fixed-size ring buffer). Applications: BFS traversal, task scheduling, "
            "rate limiting, print spooling, producer-consumer problems."
        ),
    },

    # ── Trees ─────────────────────────────────────────────────────────────────
    {
        "id": "bst_intro",
        "topic": "Binary Search Trees",
        "type": "concept",
        "title": "Binary Search Tree Properties",
        "content": (
            "A Binary Search Tree (BST) is a binary tree where every node satisfies: all values in "
            "the left subtree < node value < all values in the right subtree. This invariant enables "
            "O(log n) average-case search, insertion, and deletion (O(n) worst case for a degenerate "
            "tree / sorted input). In-order traversal of a BST yields elements in sorted order. "
            "BST deletion has three cases: node is a leaf (simply remove), node has one child "
            "(replace with child), node has two children (replace with in-order successor or "
            "predecessor, then delete that node)."
        ),
    },
    {
        "id": "bst_traversals",
        "topic": "Binary Search Trees",
        "type": "operations",
        "title": "Tree Traversal Algorithms",
        "content": (
            "In-order (Left → Root → Right): yields sorted sequence for BSTs. "
            "Pre-order (Root → Left → Right): useful for serialization/copying a tree. "
            "Post-order (Left → Right → Root): useful for deletion (process children before parent). "
            "Level-order (BFS): uses a queue; visits nodes layer by layer — useful for finding "
            "height, checking completeness. "
            "Recursive DFS traversals have O(n) time and O(h) space where h is height. "
            "Iterative implementations use an explicit stack (DFS) or queue (BFS)."
        ),
    },
    {
        "id": "avl_intro",
        "topic": "AVL Trees",
        "type": "concept",
        "title": "AVL Trees — Self-Balancing BST",
        "content": (
            "An AVL tree is a self-balancing BST where the balance factor (height(left) - height(right)) "
            "of every node is in {-1, 0, 1}. After each insertion or deletion, rotations restore "
            "balance. Four rotation types: LL (right rotation), RR (left rotation), LR (left-right), "
            "RL (right-left). AVL trees guarantee O(log n) for search, insert, delete in all cases. "
            "Height of an AVL tree with n nodes is at most 1.44 × log₂(n). Trade-off: stricter "
            "balance than Red-Black trees means more rotations on insertion/deletion but faster lookup."
        ),
    },

    # ── Heaps ─────────────────────────────────────────────────────────────────
    {
        "id": "heap_intro",
        "topic": "Heaps",
        "type": "concept",
        "title": "Binary Heap and Priority Queue",
        "content": (
            "A binary heap is a complete binary tree stored as an array. For a max-heap, every "
            "parent ≥ its children; for a min-heap, every parent ≤ its children. "
            "Array indexing (0-based): left child of i → 2i+1; right child → 2i+2; parent → (i-1)//2. "
            "Operations: insert O(log n) (append + sift up), extract-max/min O(log n) (swap root "
            "with last, remove last, sift down), peek O(1). Build heap from array: O(n) using "
            "Floyd's algorithm (sift down from n//2 to 0). Python's heapq module is a min-heap. "
            "Heapsort is O(n log n) time, O(1) space but not cache-friendly."
        ),
    },

    # ── Graphs ────────────────────────────────────────────────────────────────
    {
        "id": "graph_intro",
        "topic": "Graphs",
        "type": "concept",
        "title": "Graph Representations and Terminology",
        "content": (
            "A graph G = (V, E) consists of vertices V and edges E. Directed graphs have ordered "
            "pairs; undirected have unordered pairs. Weighted graphs assign numeric values to edges. "
            "Representations: adjacency matrix (V×V, O(V²) space, O(1) edge lookup), adjacency list "
            "(dict/list of neighbors, O(V+E) space, O(degree) neighbor iteration). "
            "Degree: for undirected, number of edges at a vertex. For directed: in-degree (edges "
            "coming in) and out-degree (edges going out). "
            "Special graphs: DAG (directed acyclic graph, enables topological sort), bipartite "
            "(2-colorable, useful for matching problems), complete graph K_n has n(n-1)/2 edges."
        ),
    },
    {
        "id": "graph_algorithms",
        "topic": "Graphs",
        "type": "operations",
        "title": "BFS, DFS, Dijkstra, and Topological Sort",
        "content": (
            "BFS (Breadth-First Search): uses a queue; finds shortest path in unweighted graphs. "
            "Time O(V+E), Space O(V). DFS (Depth-First Search): uses stack/recursion; detects cycles, "
            "finds connected components. Time O(V+E), Space O(V). "
            "Dijkstra's algorithm: single-source shortest path in weighted graphs with non-negative "
            "edges. Uses a min-heap. Time O((V+E) log V) with a binary heap. "
            "Topological sort (DAG only): Kahn's algorithm uses in-degree counting + queue; "
            "DFS-based sorts by finish time. Used for build systems, dependency resolution. "
            "Bellman-Ford handles negative weights, detects negative cycles, O(VE)."
        ),
    },

    # ── Hashing ───────────────────────────────────────────────────────────────
    {
        "id": "hashing_intro",
        "topic": "Hash Tables",
        "type": "concept",
        "title": "Hash Tables and Collision Resolution",
        "content": (
            "A hash table maps keys to values using a hash function h(key) → index. "
            "Average-case O(1) for insert, delete, lookup; O(n) worst case if many collisions. "
            "Load factor α = n/m (n items, m buckets). Rehashing doubles capacity when α > 0.7. "
            "Collision resolution: Chaining (each bucket is a linked list — simple, handles high "
            "load factors); Open addressing (probe for next open slot) — Linear probing (primary "
            "clustering), Quadratic probing (secondary clustering), Double hashing (two hash "
            "functions, best distribution). Python dict uses open addressing with pseudo-random "
            "probing. A good hash function distributes keys uniformly and is deterministic."
        ),
    },

    # ── Sorting ───────────────────────────────────────────────────────────────
    {
        "id": "sorting_comparison",
        "topic": "Sorting Algorithms",
        "type": "concept",
        "title": "Sorting Algorithm Comparison",
        "content": (
            "Bubble Sort: O(n²) time, O(1) space — swap adjacent elements; simple but inefficient. "
            "Selection Sort: O(n²) time, O(1) space — find min, swap to front; fewer swaps than bubble. "
            "Insertion Sort: O(n²) worst, O(n) best (nearly sorted); O(1) space; stable; good for small n. "
            "Merge Sort: O(n log n) always; O(n) space; stable; divide-and-conquer; great for linked lists. "
            "Quick Sort: O(n log n) average, O(n²) worst (bad pivot); O(log n) space; in-place; "
            "cache-friendly; pivot selection (median-of-3 or random) mitigates worst case. "
            "Heap Sort: O(n log n) always; O(1) space; not stable; in-place. "
            "Counting/Radix Sort: O(n+k) — not comparison-based; only for integers/bounded ranges."
        ),
    },
    {
        "id": "sorting_misconceptions",
        "topic": "Sorting Algorithms",
        "type": "misconceptions",
        "title": "Sorting Misconceptions",
        "content": (
            "Misconception 1: Quick sort is always O(n log n). Truth: worst case is O(n²) with a "
            "bad pivot (e.g., always smallest/largest element on sorted input). "
            "Misconception 2: Merge sort uses no extra space. Truth: it needs O(n) auxiliary space "
            "for the merge step. Misconception 3: A stable sort preserves insertion order only. "
            "Truth: stability means equal-key elements retain their original relative order, which "
            "matters in multi-key sorts (e.g., sort by last name then first name). "
            "Misconception 4: Python's sort is merge sort. Truth: Python uses Timsort, a hybrid of "
            "merge sort and insertion sort optimized for real-world partially sorted data."
        ),
    },

    # ── Dynamic Programming ───────────────────────────────────────────────────
    {
        "id": "dp_intro",
        "topic": "Dynamic Programming",
        "type": "concept",
        "title": "Dynamic Programming — Memoization vs Tabulation",
        "content": (
            "Dynamic programming (DP) breaks a problem into overlapping subproblems and stores "
            "solutions to avoid recomputation. Two approaches: "
            "Top-down (memoization): recursive calls with a cache (dict or @functools.lru_cache). "
            "Bottom-up (tabulation): iterative, fills a table from base cases upward — no recursion "
            "overhead, better space control. "
            "DP prerequisites: optimal substructure (optimal solution built from optimal subproblems) "
            "and overlapping subproblems. Classic problems: Fibonacci (O(n) vs O(2^n) naive), "
            "0/1 Knapsack, Longest Common Subsequence, Coin Change, Edit Distance, Longest "
            "Increasing Subsequence. State design is the hardest part — define what dp[i] represents "
            "clearly before writing recurrences."
        ),
    },
]


QUIZ_BANK = [
    # Arrays
    {
        "id": "q_array_1",
        "topic": "Arrays",
        "difficulty": "beginner",
        "question": "What is the time complexity of accessing an element at index i in an array?",
        "answer": "O(1) — constant time, because the memory address is computed directly as base_address + i × element_size.",
        "hint": "Think about how the CPU calculates where an element is in memory given its index.",
        "common_mistakes": ["O(n)", "O(log n)"],
    },
    {
        "id": "q_array_2",
        "topic": "Arrays",
        "difficulty": "intermediate",
        "question": "Why is inserting at the beginning of an array O(n) rather than O(1)?",
        "answer": "All existing elements must be shifted one position to the right to make room for the new element, which requires n operations.",
        "hint": "Imagine physically pushing n cards to the right to make space at position 0.",
        "common_mistakes": ["Because arrays are fixed size", "Because the index changes"],
    },
    {
        "id": "q_array_3",
        "topic": "Arrays",
        "difficulty": "advanced",
        "question": "Explain why dynamic arrays (like Python lists) have O(1) amortized append, even though some appends take O(n) time.",
        "answer": "Doubling strategy: when capacity is exceeded, the array doubles. The expensive O(n) copy happens rarely — after 2^k appends, only k doublings occur. Spreading the cost gives amortized O(1) per append.",
        "hint": "Consider how many times any single element is copied over the course of n appends.",
        "common_mistakes": ["It's always O(1)", "Amortized means average per call"],
    },
    # Linked Lists
    {
        "id": "q_ll_1",
        "topic": "Linked Lists",
        "difficulty": "beginner",
        "question": "What is the time complexity of inserting a node at the head of a singly linked list?",
        "answer": "O(1) — you create a new node, set its next to the current head, then update the head pointer. No traversal needed.",
        "hint": "Do you need to look at any other nodes to add at the head?",
        "common_mistakes": ["O(n)", "O(log n)"],
    },
    {
        "id": "q_ll_2",
        "topic": "Linked Lists",
        "difficulty": "intermediate",
        "question": "Describe Floyd's cycle detection algorithm and its time/space complexity.",
        "answer": "Use two pointers: slow (moves 1 step) and fast (moves 2 steps). If a cycle exists, they will eventually meet. If fast reaches None, no cycle. Time: O(n). Space: O(1) — only two pointers regardless of list size.",
        "hint": "Think of a runner on a circular track — a faster runner will eventually lap a slower one.",
        "common_mistakes": ["Uses a set to track visited nodes (that's O(n) space)", "O(n²) time"],
    },
    # Trees
    {
        "id": "q_bst_1",
        "topic": "Binary Search Trees",
        "difficulty": "beginner",
        "question": "What traversal order visits BST nodes in ascending sorted order?",
        "answer": "In-order traversal (Left → Root → Right) visits a BST's nodes in ascending sorted order.",
        "hint": "There are three DFS traversal types. Which one visits the left subtree, then the root, then the right subtree?",
        "common_mistakes": ["Pre-order", "Post-order", "Level-order"],
    },
    {
        "id": "q_bst_2",
        "topic": "Binary Search Trees",
        "difficulty": "intermediate",
        "question": "What is the worst-case time complexity for BST search, and when does it occur?",
        "answer": "O(n) — occurs when the tree is completely unbalanced (degenerate tree), for example when inserting already-sorted data, making it effectively a linked list.",
        "hint": "Imagine inserting 1, 2, 3, 4, 5 into a BST in order — what does the tree look like?",
        "common_mistakes": ["Always O(log n)", "O(n log n)"],
    },
    # Sorting
    {
        "id": "q_sort_1",
        "topic": "Sorting Algorithms",
        "difficulty": "beginner",
        "question": "Which sorting algorithm is most efficient for nearly-sorted data and why?",
        "answer": "Insertion sort — it runs in O(n) on nearly-sorted data because each element needs only a few swaps to reach its correct position. The inner loop terminates early when no swap is needed.",
        "hint": "Which algorithm builds a sorted portion one element at a time by sliding each new element to its correct position?",
        "common_mistakes": ["Merge sort", "Quick sort", "Bubble sort"],
    },
    # Graphs
    {
        "id": "q_graph_1",
        "topic": "Graphs",
        "difficulty": "intermediate",
        "question": "What is the difference between BFS and DFS, and when would you prefer each?",
        "answer": "BFS uses a queue and explores level by level — ideal for shortest path in unweighted graphs. DFS uses a stack/recursion and goes deep before backtracking — ideal for cycle detection, topological sort, and connectivity. BFS guarantees shortest hop count; DFS uses less memory for sparse deep graphs.",
        "hint": "Think about what data structure each uses and how that affects which nodes are visited first.",
        "common_mistakes": ["BFS uses a stack", "DFS finds shortest path"],
    },
    # DP
    {
        "id": "q_dp_1",
        "topic": "Dynamic Programming",
        "difficulty": "advanced",
        "question": "What are the two necessary conditions for a problem to be solvable by dynamic programming?",
        "answer": "1) Optimal substructure: an optimal solution to the problem can be constructed from optimal solutions to its subproblems. 2) Overlapping subproblems: the same subproblems are solved multiple times during recursion, making memoization beneficial.",
        "hint": "DP is an optimization over naive recursion — think about what properties make caching subproblem solutions worthwhile.",
        "common_mistakes": ["Only needs recursion", "Greedy always works if DP works"],
    },
]


def generate_materials():
    os.makedirs(os.path.dirname(MATERIALS_PATH), exist_ok=True)
    with open(MATERIALS_PATH, "w") as f:
        json.dump({"materials": COURSE_MATERIALS, "quiz_bank": QUIZ_BANK}, f, indent=2)
    print(f"✓ Generated {len(COURSE_MATERIALS)} course materials and {len(QUIZ_BANK)} quiz questions.")
    print(f"  Saved to {MATERIALS_PATH}")


if __name__ == "__main__":
    generate_materials()