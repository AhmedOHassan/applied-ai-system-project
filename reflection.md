# PawPal+ Project Reflection

## 1. System Design

Core Actions:

- Add owner and pet info
- Add/Edit tasks
- Generate a schedule

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

My initial UML design was pretty straightforward, I tried to model the app the same way you'd naturally think about pet care in real life.

I went with 4 classes:

- **Owner** is basically the person using the app. They have a name, a limited amount of free time each day, and some preferences about how they like things done.

- **Pet** is their animal. Stores the basics, name, species, age, plus any notes like "takes medication" or "anxious around strangers."

- **Task** is where the real detail lives. Every care activity (a walk, a feeding, grooming) gets its own task with a duration, a priority level, and optionally a preferred time of day. It also tracks whether it's been done yet.

- **Schedule** is the brain of the app. It looks at the owner's available time and the pet's list of tasks, then builds a realistic daily plan, starting with the highest priority tasks and working down until time runs out. It also keeps notes on why certain tasks made the cut and others didn't.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

The biggest one was with Schedule. I originally built it to handle one pet at a time, which seemed fine at first. But then I thought, what if someone has both a dog and a cat? They're not going to have separate time budgets for each one, it all comes from the same day. So I changed it to take a list of pets instead, and now the schedule pulls tasks from all of them together and figures out what fits.

I also rethought where available_minutes lives. I had it on Owner, like "this person has 90 minutes a day", and that makes sense on the surface. But then I realized, what about a busy Monday versus a lazy Sunday? You'd have to go in and change the owner's data every single day, which is annoying. So now the Schedule has its own time value that just defaults to whatever the owner set, but you can override it per day without touching anything else.

The back-references were another thing I didn't plan for originally. A Task didn't know which pet it belonged to, and a Pet didn't know who its owner was. That felt fine in isolation, but the moment I imagined actually building the UI, like showing "Buddy's tasks" or filtering by owner, I realized the data needed to flow both ways, not just top-down.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

The scheduler considers two main constraints: available time and task priority. It sorts all tasks from highest to lowest priority, then greedily picks them until the owner's time runs out. Preferred time of day is also stored on each task, but it influences display and conflict detection rather than whether a task gets scheduled at all.

Time and priority felt like the obvious starting point because they're the two things that actually determine whether something gets done, you can have a perfectly timed plan but if you only have 30 minutes, some tasks just won't happen, and priority decides which ones survive that cut.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

The conflict detection only flags tasks that share the same time label, "morning", "afternoon", or "evening", rather than checking whether their actual durations overlap on a real clock. So two morning tasks are always flagged as a conflict even if one takes 5 minutes and the other starts right after.

For this app that's fine. Most pet owners don't schedule their day down to the minute, they think in rough blocks. Flagging anything in the same block and letting the owner decide is more practical than trying to calculate exact start and end times, which would require a lot more data the app doesn't have anyway.
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

I tested three core behaviors: sorting (tasks come back in the right time order), recurrence (completing a daily task automatically creates one for the next day), and conflict detection (the scheduler flags when two tasks land in the same time slot). 

These mattered because they're what the app actually does every day, if any of them break, the schedule either looks wrong, loses tasks silently, or misses overlaps the owner is counting on the app to catch.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

Pretty confident in the happy path, all five tests pass and the core logic holds up. That said, I know there are gaps: I haven't tested what happens when available time is zero, when two pets have tasks in the same slot, or when a recurring task rolls over at the end of a month. Those are the ones I'd go after next, because they're the situations where date math and edge-of-budget logic are most likely to quietly break.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
