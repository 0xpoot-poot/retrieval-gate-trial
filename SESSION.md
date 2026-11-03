# What we will talk about, in order

**Before you touch the code**
- The agreement says the filter must narrow the candidates, not the results. In your own words, what is the
  difference, and why would a firm write that?
- You have a function that takes a user, a matter and a query and returns passages. How would you set out to prove it
  obeys nine access rules? What is your first test?
- What could a test that only looks at the returned passages never catch?

**While you work**
- Show us a leak the moment you have one. Which rule, which user, which passage, how you know.
- How does your test decide what a user is allowed to see? If you derived that from the same rules the code claims to
  implement, what have you proved?
- One of the flaws never shows up in the results. How would you look for it? (The `reranker` parameter and the audit
  log are both yours to use.)
- Suppose the cache key now includes the user but not the matter. Does any of your tests catch that? Change one so it
  does.
- The keyword search counts how often each word appears across the whole index, including walled matters. Is that a
  leak? Does it matter?

**The wider picture**
- Of everything in `RULES.md` Part B, which three would you escalate first, to whom, and what would you propose?
- In production this is PostgreSQL with pgvector. With an approximate-nearest-neighbour index and a WHERE clause on
  the matter, where does the filtering actually happen, and is what goes wrong a leak or a recall problem?

**At the end**
- What do your tests not prove?
- Where did your tools help, and where did they get something wrong that you had to fix?
