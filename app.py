import streamlit as st
from datetime import date
from pawpal_system import Owner, Pet, Task, Schedule

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.title("🐾 PawPal+")
st.caption("Your daily pet care planner")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None

if "pets" not in st.session_state:
    st.session_state.pets = []       # list of Pet objects — supports multiple pets

if "tasks" not in st.session_state:
    st.session_state.tasks = []      # flat list of all Task objects for display

if "schedule" not in st.session_state:
    st.session_state.schedule = None

# ---------------------------------------------------------------------------
# Section 1 — Owner
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.subheader("👤 Owner")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        owner_name = st.text_input("Owner name")
    with c2:
        available_minutes = st.number_input(
            "Available time today (min)", min_value=10, max_value=480, value=None, placeholder="e.g. 90"
        )
    with c3:
        prefer_morning = st.checkbox("Prefer morning tasks", value=False)

    if st.button("Save owner"):
        st.session_state.owner = Owner(
            name=owner_name,
            available_minutes=int(available_minutes),
            preferences={"prefer_morning": prefer_morning},
        )
        # Reset downstream state when owner changes
        st.session_state.pets = []
        st.session_state.tasks = []
        st.session_state.schedule = None
        st.success(f"Owner saved: **{owner_name}** — {available_minutes} min available today")

# ---------------------------------------------------------------------------
# Section 2 — Pets  (multiple pets supported, as noted in reflection)
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.subheader("🐾 Pets")

    if st.session_state.owner is None:
        st.info("Save an owner first.")
    else:
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            pet_name = st.text_input("Pet name", key="pet_name_input")
        with c2:
            species = st.selectbox(
                "Species", ["dog", "cat", "rabbit", "other"], key="pet_species_input"
            )
        with c3:
            st.write("")   # vertical alignment spacer
            add_pet = st.button("Add pet")

        if add_pet:
            existing_names = [p.name for p in st.session_state.pets]
            if pet_name in existing_names:
                st.warning(f"A pet named **{pet_name}** already exists.")
            else:
                pet = Pet(name=pet_name, species=species, age=0)
                st.session_state.owner.add_pet(pet)
                st.session_state.pets.append(pet)
                st.success(f"Added **{pet_name}** ({species})")

        if st.session_state.pets:
            species_icons = {"dog": "🐶", "cat": "🐱", "rabbit": "🐰", "other": "🐾"}
            cols = st.columns(min(len(st.session_state.pets), 4))
            for i, pet in enumerate(st.session_state.pets):
                icon = species_icons.get(pet.species, "🐾")
                cols[i % 4].metric(label=f"{icon} {pet.name}", value=pet.species.capitalize())
        else:
            st.caption("No pets added yet.")

# ---------------------------------------------------------------------------
# Section 3 — Task management
# ---------------------------------------------------------------------------

with st.container(border=True):
    st.subheader("📋 Tasks")

    if not st.session_state.pets:
        st.info("Add at least one pet before creating tasks.")
    else:
        priority_map = {"low": 1, "medium": 2, "high": 3}

        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
        with c1:
            task_title = st.text_input("Task name")
        with c2:
            assign_to = st.selectbox(
                "Assign to pet", [p.name for p in st.session_state.pets], key="assign_pet"
            )
        with c3:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=None, placeholder="e.g. 20")
        with c4:
            priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=2)
        with c5:
            preferred_time = st.selectbox("Time", ["morning", "afternoon", "evening"])

        if st.button("Add task"):
            task = Task(
                name=task_title,
                category="general",
                duration_minutes=int(duration),
                priority=priority_map[priority_label],
                preferred_time=preferred_time,
            )
            target_pet = next(p for p in st.session_state.pets if p.name == assign_to)
            target_pet.add_task(task)
            st.session_state.tasks.append(task)
            st.success(f"Added **{task_title}** → {assign_to}")

        # Current task list with Remove + Edit
        if st.session_state.tasks:
            st.markdown("**Current tasks**")

            h1, h2, h3, h4, h5, h6 = st.columns([3, 2, 2, 1, 2, 1])
            h1.markdown("**Task**");          h2.markdown("**Pet**")
            h3.markdown("**Duration (min)**"); h4.markdown("**Priority**")
            h5.markdown("**Preferred time**"); h6.markdown("**Action**")

            for i, task in enumerate(st.session_state.tasks):
                c1, c2, c3, c4, c5, c6 = st.columns([3, 2, 2, 1, 2, 1])
                c1.write(task.name);          c2.write(task.pet_name)
                c3.write(task.duration_minutes); c4.write(task.priority)
                c5.write(task.preferred_time or "—")
                if c6.button("Remove", key=f"remove_{i}"):
                    owner_pet = next((p for p in st.session_state.pets if p.name == task.pet_name), None)
                    if owner_pet:
                        owner_pet.remove_task(task)
                    st.session_state.tasks.pop(i)
                    st.rerun()

            with st.expander("✏️ Edit a task", expanded=True):
                task_names = [t.name for t in st.session_state.tasks]
                selected_name = st.selectbox("Select task to edit", task_names, key="edit_select")
                selected_task = next(t for t in st.session_state.tasks if t.name == selected_name)

                st.caption(f"Current — name: **{selected_task.name}** | "
                           f"duration: **{selected_task.duration_minutes} min** | "
                           f"priority: **{selected_task.priority}** | "
                           f"time: **{selected_task.preferred_time or '—'}**")

                # Keys include selected_name so widgets reset when you switch tasks
                e1, e2, e3, e4 = st.columns(4)
                with e1:
                    new_name = st.text_input(
                        "New name", value="",
                        key=f"edit_name_{selected_name}"
                    )
                with e2:
                    new_duration = st.number_input(
                        "Duration (min)", min_value=1, max_value=240,
                        value=None,
                        key=f"edit_dur_{selected_name}"
                    )
                with e3:
                    new_priority_label = st.selectbox(
                        "Priority", ["", "low", "medium", "high"],
                        index=0, key=f"edit_pri_{selected_name}"
                    )
                with e4:
                    new_time = st.selectbox(
                        "Preferred time", ["morning", "afternoon", "evening"],
                        index=0, key=f"edit_time_{selected_name}"
                    )

                if st.button("Save edits"):
                    if not new_name and new_duration is None and not new_priority_label:
                        st.warning("Change at least one field before saving.")
                    else:
                        selected_task.name           = new_name or selected_task.name
                        selected_task.duration_minutes = int(new_duration) if new_duration is not None else selected_task.duration_minutes
                        selected_task.priority       = priority_map[new_priority_label] if new_priority_label else selected_task.priority
                        selected_task.preferred_time = new_time
                        st.success(f"Updated: {selected_task.name}")
                        st.rerun()
        else:
            st.info("No tasks yet. Add one above.")

# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# ---------------------------------------------------------------------------

st.divider()
st.subheader("🗓️ Build Schedule")

col_gen, col_reset = st.columns([3, 1])
with col_gen:
    if st.button("Generate schedule", type="primary"):
        if st.session_state.owner is None:
            st.warning("Save an owner first.")
        elif not st.session_state.pets:
            st.warning("Add at least one pet first.")
        elif not st.session_state.tasks:
            st.warning("Add at least one task before generating a schedule.")
        else:
            schedule = Schedule(
                owner=st.session_state.owner,
                pets=st.session_state.pets,   # all pets passed in — multi-pet support
                date=date.today(),
            )
            schedule.generate()
            st.session_state.schedule = schedule
            st.success("Schedule generated!")

with col_reset:
    if st.session_state.schedule is not None:
        if st.button("Reset day"):
            st.session_state.schedule.reset_all_tasks()   # calls task.reset() on every task
            st.success("All tasks reset to pending.")
            st.rerun()

# ---------------------------------------------------------------------------
# Display schedule (lives in session state, survives re-renders)
# ---------------------------------------------------------------------------

if st.session_state.schedule is not None:
    schedule = st.session_state.schedule

    # Summary metrics row
    total     = schedule.get_total_duration()
    available = st.session_state.owner.available_minutes
    remaining = available - total
    m1, m2, m3 = st.columns(3)
    m1.metric("Planned time",    f"{total} min")
    m2.metric("Available time",  f"{available} min")
    m3.metric("Time remaining",  f"{remaining} min", delta=remaining, delta_color="normal")

    # Conflict warnings — prominent, above the task table
    conflicts = schedule.detect_conflicts()
    if conflicts:
        st.markdown("### ⚠️ Scheduling Conflicts")
        for conflict in conflicts:
            st.warning(conflict)

    # Filter + sort controls
    st.markdown("### Planned Tasks")
    f1, f2 = st.columns(2)
    with f1:
        status_filter = st.selectbox(
            "Filter by status", ["All", "Pending", "Completed"], key="filter_status"
        )
    with f2:
        view_order = st.selectbox(
            "Sort by", ["Time of day", "Priority"], key="sort_order"
        )

    completed_arg = None if status_filter == "All" else (status_filter == "Completed")
    filtered = schedule.filter_tasks(completed=completed_arg)

    time_order = {"morning": 0, "afternoon": 1, "evening": 2, "": 3}
    if view_order == "Time of day":
        display_tasks = sorted(filtered, key=lambda t: time_order.get(t.preferred_time, 3))
    else:
        display_tasks = sorted(filtered, key=lambda t: t.priority, reverse=True)

    if display_tasks:
        time_label = {"morning": "🌅 Morning", "afternoon": "☀️ Afternoon", "evening": "🌙 Evening", "": "—"}
        pri_label  = {1: "🟢 Low", 2: "🟡 Medium", 3: "🔴 High"}

        h1, h2, h3, h4, h5, h6 = st.columns([3, 2, 2, 2, 2, 1])
        h1.markdown("**Task**");          h2.markdown("**Pet**")
        h3.markdown("**Priority**");      h4.markdown("**Time slot**")
        h5.markdown("**Duration (min)**"); h6.markdown("**Done?**")

        for task in display_tasks:
            c1, c2, c3, c4, c5, c6 = st.columns([3, 2, 2, 2, 2, 1])
            # Strike through completed task names
            c1.write("~~" + task.name + "~~" if task.is_completed else task.name)
            c2.write(task.pet_name)
            c3.write(pri_label.get(task.priority, str(task.priority)))
            c4.write(time_label.get(task.preferred_time, "—"))
            c5.write(task.duration_minutes)
            btn_label = "✓" if task.is_completed else "Complete"
            if c6.button(btn_label, key=f"complete_{task.name}", disabled=task.is_completed):
                next_task = schedule.complete_task(task)   # mark_complete + next_occurrence
                if next_task:
                    owner_pet = next((p for p in st.session_state.pets if p.name == task.pet_name), None)
                    if owner_pet:
                        st.session_state.tasks.append(next_task)
                    st.info(f"Next '{task.name}' auto-scheduled for {next_task.due_date}.")
                st.rerun()
    else:
        st.info("No tasks match the current filter.")

    # Reasoning log collapsed by default — keeps the view clean
    with st.expander("🧠 Scheduling Reasoning"):
        for reason in schedule.reasoning:
            if reason.startswith("[+]"):
                st.success(reason)
            elif reason.startswith("[-]"):
                st.info(reason)
            else:
                st.write(reason)
