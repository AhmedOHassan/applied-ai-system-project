from datetime import date, timedelta
from pawpal_system import Task, Pet, Owner, Schedule


# ---------------------------------------------------------------------------
# Test 1: Task Completion
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    """Calling mark_complete() should flip is_completed from False to True."""
    task = Task(name="Morning Walk", category="walk", duration_minutes=30, priority=3)

    # Task should start as not completed
    assert task.is_completed is False

    task.mark_complete()

    # Task should now be marked as done
    assert task.is_completed is True


# ---------------------------------------------------------------------------
# Test 2: Task Addition
# ---------------------------------------------------------------------------

def test_add_task_increases_pet_task_count():
    """Adding a task to a Pet should increase its task list by one."""
    pet = Pet(name="Buddy", species="dog", age=3)

    # Pet starts with no tasks
    assert len(pet.get_tasks()) == 0

    pet.add_task(Task(name="Breakfast Feeding", category="feeding", duration_minutes=10, priority=3))

    # Pet should now have exactly one task
    assert len(pet.get_tasks()) == 1


# ---------------------------------------------------------------------------
# Test 3: Sorting Correctness
# ---------------------------------------------------------------------------

def test_sort_by_time_returns_chronological_order():
    """sort_by_time() should return tasks in morning → afternoon → evening order."""
    owner = Owner(name="Alex", available_minutes=120)
    pet = Pet(name="Buddy", species="dog", age=3)
    owner.add_pet(pet)

    evening_task  = Task(name="Evening Walk",    category="walk",    duration_minutes=30, priority=2, preferred_time="evening")
    morning_task  = Task(name="Morning Feeding", category="feeding", duration_minutes=15, priority=2, preferred_time="morning")
    afternoon_task = Task(name="Afternoon Meds", category="meds",   duration_minutes=10, priority=2, preferred_time="afternoon")

    # Add in deliberately wrong order to confirm sort fixes it
    for task in (evening_task, afternoon_task, morning_task):
        pet.add_task(task)

    schedule = Schedule(owner=owner, pets=[pet], date=date.today())
    schedule.generate()

    sorted_tasks = schedule.sort_by_time()

    assert [t.preferred_time for t in sorted_tasks] == ["morning", "afternoon", "evening"]


# ---------------------------------------------------------------------------
# Test 4: Recurrence Logic
# ---------------------------------------------------------------------------

def test_daily_task_recurrence_schedules_next_day():
    """Completing a daily task should create a new task due exactly one day later."""
    owner = Owner(name="Alex", available_minutes=120)
    pet = Pet(name="Buddy", species="dog", age=3)
    owner.add_pet(pet)

    today = date.today()
    task = Task(name="Morning Walk", category="walk", duration_minutes=30, priority=2,
                frequency="daily", due_date=today)
    pet.add_task(task)

    schedule = Schedule(owner=owner, pets=[pet], date=today)
    schedule.generate()

    next_task = schedule.complete_task(task)

    # A new task must have been created
    assert next_task is not None
    # It should be due tomorrow
    assert next_task.due_date == today + timedelta(days=1)
    # The pet's task list should now contain the original + the new occurrence
    assert next_task in pet.get_tasks()


# ---------------------------------------------------------------------------
# Test 5: Conflict Detection
# ---------------------------------------------------------------------------

def test_detect_conflicts_flags_duplicate_time_slots():
    """Two planned tasks sharing the same preferred_time should produce a conflict warning."""
    owner = Owner(name="Alex", available_minutes=120)
    pet = Pet(name="Buddy", species="dog", age=3)
    owner.add_pet(pet)

    task_a = Task(name="Morning Walk",    category="walk",    duration_minutes=30, priority=2, preferred_time="morning")
    task_b = Task(name="Morning Feeding", category="feeding", duration_minutes=15, priority=2, preferred_time="morning")

    pet.add_task(task_a)
    pet.add_task(task_b)

    schedule = Schedule(owner=owner, pets=[pet], date=date.today())
    schedule.generate()

    warnings = schedule.detect_conflicts()

    # At least one conflict warning must be raised
    assert len(warnings) >= 1
    # The warning should mention the conflicting slot
    assert any("morning" in w for w in warnings)
