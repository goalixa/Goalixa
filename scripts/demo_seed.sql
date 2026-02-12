-- Goalixa demo seed data (Postgres)
-- Replace {{user_id}} with the target user id before executing.

-- Labels
INSERT INTO labels (user_id, name, color, created_at) VALUES
  ({{user_id}}, 'Deep Work', '#1f6feb', (NOW() AT TIME ZONE 'UTC')),
  ({{user_id}}, 'Quick Win', '#f2a900', (NOW() AT TIME ZONE 'UTC')),
  ({{user_id}}, 'Research', '#22c55e', (NOW() AT TIME ZONE 'UTC')),
  ({{user_id}}, 'Meetings', '#a855f7', (NOW() AT TIME ZONE 'UTC')),
  ({{user_id}}, 'Admin', '#e85d75', (NOW() AT TIME ZONE 'UTC'));

-- Projects
INSERT INTO projects (user_id, name, created_at) VALUES
  ({{user_id}}, 'Product Launch Q2', (NOW() AT TIME ZONE 'UTC') - INTERVAL '12 days'),
  ({{user_id}}, 'Client Retainer', (NOW() AT TIME ZONE 'UTC') - INTERVAL '20 days'),
  ({{user_id}}, 'Personal Growth', (NOW() AT TIME ZONE 'UTC') - INTERVAL '8 days');

-- Project labels
INSERT INTO project_labels (project_id, label_id)
SELECT p.id, l.id
FROM projects p
JOIN labels l ON l.user_id = p.user_id
WHERE p.user_id = {{user_id}} AND p.name = 'Product Launch Q2'
  AND l.name IN ('Deep Work', 'Research');

INSERT INTO project_labels (project_id, label_id)
SELECT p.id, l.id
FROM projects p
JOIN labels l ON l.user_id = p.user_id
WHERE p.user_id = {{user_id}} AND p.name = 'Client Retainer'
  AND l.name IN ('Meetings', 'Admin');

INSERT INTO project_labels (project_id, label_id)
SELECT p.id, l.id
FROM projects p
JOIN labels l ON l.user_id = p.user_id
WHERE p.user_id = {{user_id}} AND p.name = 'Personal Growth'
  AND l.name IN ('Deep Work');

-- Tasks
INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'Finalize landing page', (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days', p.id, 'active', NULL
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Product Launch Q2';

INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'Write onboarding emails', (NOW() AT TIME ZONE 'UTC') - INTERVAL '6 days', p.id, 'active', NULL
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Product Launch Q2';

INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'QA signup flow', (NOW() AT TIME ZONE 'UTC') - INTERVAL '5 days', p.id, 'active', NULL
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Product Launch Q2';

INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'Archive old assets', (NOW() AT TIME ZONE 'UTC') - INTERVAL '10 days', p.id, 'completed', ((NOW() AT TIME ZONE 'UTC') - INTERVAL '1 day')
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Product Launch Q2';

INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'Weekly status report', (NOW() AT TIME ZONE 'UTC') - INTERVAL '4 days', p.id, 'active', NULL
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Client Retainer';

INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'Dashboard polish', (NOW() AT TIME ZONE 'UTC') - INTERVAL '3 days', p.id, 'active', NULL
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Client Retainer';

INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'Stakeholder review', (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days', p.id, 'active', NULL
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Client Retainer';

INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'Read 20 pages', (NOW() AT TIME ZONE 'UTC') - INTERVAL '6 days', p.id, 'active', NULL
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Personal Growth';

INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'Strength workout', (NOW() AT TIME ZONE 'UTC') - INTERVAL '4 days', p.id, 'active', NULL
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Personal Growth';

INSERT INTO tasks (user_id, name, created_at, project_id, status, completed_at)
SELECT {{user_id}}, 'Weekly planning', (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days', p.id, 'active', NULL
FROM projects p WHERE p.user_id = {{user_id}} AND p.name = 'Personal Growth';

-- Task labels
INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'Finalize landing page'
  AND l.name IN ('Deep Work', 'Research');

INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'Write onboarding emails'
  AND l.name IN ('Quick Win');

INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'QA signup flow'
  AND l.name IN ('Deep Work', 'Admin');

INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'Archive old assets'
  AND l.name IN ('Admin');

INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'Weekly status report'
  AND l.name IN ('Admin');

INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'Dashboard polish'
  AND l.name IN ('Deep Work');

INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'Stakeholder review'
  AND l.name IN ('Meetings');

INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'Read 20 pages'
  AND l.name IN ('Deep Work');

INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'Strength workout'
  AND l.name IN ('Quick Win');

INSERT INTO task_labels (task_id, label_id)
SELECT t.id, l.id
FROM tasks t
JOIN labels l ON l.user_id = t.user_id
WHERE t.user_id = {{user_id}} AND t.name = 'Weekly planning'
  AND l.name IN ('Meetings');

-- Time entries
INSERT INTO time_entries (user_id, task_id, started_at, ended_at)
SELECT {{user_id}}, t.id, ((NOW() AT TIME ZONE 'UTC') - INTERVAL '5 days 2 hours'), ((NOW() AT TIME ZONE 'UTC') - INTERVAL '5 days 45 minutes')
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name = 'Finalize landing page';

INSERT INTO time_entries (user_id, task_id, started_at, ended_at)
SELECT {{user_id}}, t.id, ((NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days 3 hours'), ((NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days 1 hour 20 minutes')
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name = 'Finalize landing page';

INSERT INTO time_entries (user_id, task_id, started_at, ended_at)
SELECT {{user_id}}, t.id, ((NOW() AT TIME ZONE 'UTC') - INTERVAL '3 days 1 hour'), ((NOW() AT TIME ZONE 'UTC') - INTERVAL '3 days 5 minutes')
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name = 'QA signup flow';

INSERT INTO time_entries (user_id, task_id, started_at, ended_at)
SELECT {{user_id}}, t.id, ((NOW() AT TIME ZONE 'UTC') - INTERVAL '1 day 2 hours'), ((NOW() AT TIME ZONE 'UTC') - INTERVAL '1 day 1 hour 10 minutes')
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name = 'Dashboard polish';

INSERT INTO time_entries (user_id, task_id, started_at, ended_at)
SELECT {{user_id}}, t.id, ((NOW() AT TIME ZONE 'UTC') - INTERVAL '10 hours'), ((NOW() AT TIME ZONE 'UTC') - INTERVAL '9 hours 20 minutes')
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name = 'Weekly status report';

INSERT INTO time_entries (user_id, task_id, started_at, ended_at)
SELECT {{user_id}}, t.id, ((NOW() AT TIME ZONE 'UTC') - INTERVAL '6 hours'), ((NOW() AT TIME ZONE 'UTC') - INTERVAL '5 hours 35 minutes')
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name = 'Read 20 pages';

INSERT INTO time_entries (user_id, task_id, started_at, ended_at)
SELECT {{user_id}}, t.id, ((NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days 6 hours'), ((NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days 5 hours 20 minutes')
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name = 'Strength workout';

-- Task daily checks
INSERT INTO task_daily_checks (task_id, log_date, created_at)
SELECT t.id, TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC')
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name IN ('Weekly planning', 'Read 20 pages');

INSERT INTO task_daily_checks (task_id, log_date, created_at)
SELECT t.id, TO_CHAR(CURRENT_DATE - INTERVAL '1 day', 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC') - INTERVAL '1 day'
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name IN ('Dashboard polish');

INSERT INTO task_daily_checks (task_id, log_date, created_at)
SELECT t.id, TO_CHAR(CURRENT_DATE - INTERVAL '2 days', 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days'
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name IN ('Finalize landing page', 'QA signup flow');

INSERT INTO task_daily_checks (task_id, log_date, created_at)
SELECT t.id, TO_CHAR(CURRENT_DATE - INTERVAL '3 days', 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC') - INTERVAL '3 days'
FROM tasks t WHERE t.user_id = {{user_id}} AND t.name IN ('Strength workout');

-- Goals
INSERT INTO goals (user_id, name, description, status, priority, target_date, target_seconds, created_at)
VALUES
  ({{user_id}}, 'Launch Goalixa Beta', 'Ship a polished beta and collect early feedback.', 'active', 'high', TO_CHAR(CURRENT_DATE + INTERVAL '30 days', 'YYYY-MM-DD'), 72000, (NOW() AT TIME ZONE 'UTC') - INTERVAL '10 days'),
  ({{user_id}}, 'Build Consistent Focus Routine', 'Establish a repeatable focus rhythm each week.', 'active', 'medium', TO_CHAR(CURRENT_DATE + INTERVAL '60 days', 'YYYY-MM-DD'), 108000, (NOW() AT TIME ZONE 'UTC') - INTERVAL '15 days');

-- Goal projects
INSERT INTO goal_projects (goal_id, project_id)
SELECT g.id, p.id
FROM goals g
JOIN projects p ON p.user_id = g.user_id
WHERE g.user_id = {{user_id}} AND g.name = 'Launch Goalixa Beta' AND p.name = 'Product Launch Q2';

INSERT INTO goal_projects (goal_id, project_id)
SELECT g.id, p.id
FROM goals g
JOIN projects p ON p.user_id = g.user_id
WHERE g.user_id = {{user_id}} AND g.name = 'Build Consistent Focus Routine' AND p.name = 'Personal Growth';

-- Goal tasks
INSERT INTO goal_tasks (goal_id, task_id)
SELECT g.id, t.id
FROM goals g
JOIN tasks t ON t.user_id = g.user_id
WHERE g.user_id = {{user_id}} AND g.name = 'Launch Goalixa Beta'
  AND t.name IN ('Finalize landing page', 'Write onboarding emails', 'QA signup flow');

INSERT INTO goal_tasks (goal_id, task_id)
SELECT g.id, t.id
FROM goals g
JOIN tasks t ON t.user_id = g.user_id
WHERE g.user_id = {{user_id}} AND g.name = 'Build Consistent Focus Routine'
  AND t.name IN ('Read 20 pages', 'Strength workout', 'Weekly planning');

-- Goal subgoals
INSERT INTO goal_subgoals (goal_id, title, label, target_date, project_id, status, created_at)
SELECT g.id, 'Finalize launch checklist', 'Milestone', TO_CHAR(CURRENT_DATE + INTERVAL '14 days', 'YYYY-MM-DD'), p.id, 'pending', (NOW() AT TIME ZONE 'UTC') - INTERVAL '5 days'
FROM goals g
JOIN projects p ON p.user_id = g.user_id
WHERE g.user_id = {{user_id}} AND g.name = 'Launch Goalixa Beta' AND p.name = 'Product Launch Q2';

INSERT INTO goal_subgoals (goal_id, title, label, target_date, project_id, status, created_at)
SELECT g.id, 'Schedule beta invite', 'Outreach', TO_CHAR(CURRENT_DATE + INTERVAL '21 days', 'YYYY-MM-DD'), p.id, 'pending', (NOW() AT TIME ZONE 'UTC') - INTERVAL '4 days'
FROM goals g
JOIN projects p ON p.user_id = g.user_id
WHERE g.user_id = {{user_id}} AND g.name = 'Launch Goalixa Beta' AND p.name = 'Product Launch Q2';

INSERT INTO goal_subgoals (goal_id, title, label, target_date, project_id, status, created_at)
SELECT g.id, 'Complete 12 pomodoros', 'Consistency', TO_CHAR(CURRENT_DATE + INTERVAL '28 days', 'YYYY-MM-DD'), p.id, 'pending', (NOW() AT TIME ZONE 'UTC') - INTERVAL '6 days'
FROM goals g
JOIN projects p ON p.user_id = g.user_id
WHERE g.user_id = {{user_id}} AND g.name = 'Build Consistent Focus Routine' AND p.name = 'Personal Growth';

INSERT INTO goal_subgoals (goal_id, title, label, target_date, project_id, status, created_at)
SELECT g.id, '4 workouts per week', 'Energy', TO_CHAR(CURRENT_DATE + INTERVAL '35 days', 'YYYY-MM-DD'), p.id, 'pending', (NOW() AT TIME ZONE 'UTC') - INTERVAL '6 days'
FROM goals g
JOIN projects p ON p.user_id = g.user_id
WHERE g.user_id = {{user_id}} AND g.name = 'Build Consistent Focus Routine' AND p.name = 'Personal Growth';

-- Habits
INSERT INTO habits (user_id, name, frequency, time_of_day, reminder, notes, goal_name, subgoal_name, created_at) VALUES
  ({{user_id}}, 'Morning planning', 'Daily', 'Morning', '09:00', 'Plan the top three priorities for today.', 'Build Consistent Focus Routine', NULL, (NOW() AT TIME ZONE 'UTC') - INTERVAL '20 days'),
  ({{user_id}}, 'Workout 3x week', 'Weekdays', 'Evening', NULL, 'Keep energy steady and reduce stress.', 'Build Consistent Focus Routine', NULL, (NOW() AT TIME ZONE 'UTC') - INTERVAL '18 days'),
  ({{user_id}}, 'Inbox zero', 'Daily', 'Afternoon', NULL, 'Clear notifications before shutdown.', NULL, NULL, (NOW() AT TIME ZONE 'UTC') - INTERVAL '12 days');

-- Habit logs
INSERT INTO habit_logs (habit_id, log_date, created_at)
SELECT h.id, TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC')
FROM habits h WHERE h.user_id = {{user_id}} AND h.name IN ('Morning planning', 'Workout 3x week');

INSERT INTO habit_logs (habit_id, log_date, created_at)
SELECT h.id, TO_CHAR(CURRENT_DATE - INTERVAL '1 day', 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC') - INTERVAL '1 day'
FROM habits h WHERE h.user_id = {{user_id}} AND h.name IN ('Morning planning', 'Inbox zero');

INSERT INTO habit_logs (habit_id, log_date, created_at)
SELECT h.id, TO_CHAR(CURRENT_DATE - INTERVAL '2 days', 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days'
FROM habits h WHERE h.user_id = {{user_id}} AND h.name IN ('Morning planning', 'Workout 3x week', 'Inbox zero');

INSERT INTO habit_logs (habit_id, log_date, created_at)
SELECT h.id, TO_CHAR(CURRENT_DATE - INTERVAL '3 days', 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC') - INTERVAL '3 days'
FROM habits h WHERE h.user_id = {{user_id}} AND h.name IN ('Morning planning', 'Inbox zero');

INSERT INTO habit_logs (habit_id, log_date, created_at)
SELECT h.id, TO_CHAR(CURRENT_DATE - INTERVAL '4 days', 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC') - INTERVAL '4 days'
FROM habits h WHERE h.user_id = {{user_id}} AND h.name IN ('Morning planning', 'Workout 3x week');

-- Reminders
INSERT INTO reminders (
  user_id, title, notes, remind_date, remind_time, repeat_interval, repeat_days,
  priority, channel_toast, channel_system, play_sound, is_active, created_at
) VALUES (
  {{user_id}}, 'Weekly review', 'Reflect on wins and set next priorities.',
  TO_CHAR(CURRENT_DATE + INTERVAL '2 days', 'YYYY-MM-DD'), '09:30', 'weekly', 'Mon',
  'normal', 1, 0, 0, 1, (NOW() AT TIME ZONE 'UTC')
);

-- Daily todos
INSERT INTO daily_todos (user_id, name, log_date, created_at) VALUES
  ({{user_id}}, 'Plan top 3 tasks', TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC')),
  ({{user_id}}, 'Send client update', TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC')),
  ({{user_id}}, 'Review calendar blocks', TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD'), (NOW() AT TIME ZONE 'UTC'));

-- Weekly goals
INSERT INTO weekly_goals (user_id, title, target_seconds, week_start, week_end, status, created_at) VALUES
  ({{user_id}}, '10 hours of deep work', 36000,
   TO_CHAR(DATE_TRUNC('week', CURRENT_DATE)::date, 'YYYY-MM-DD'),
   TO_CHAR((DATE_TRUNC('week', CURRENT_DATE)::date + INTERVAL '6 days')::date, 'YYYY-MM-DD'),
   'active', (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days'),
  ({{user_id}}, 'Ship one new feature', 0,
   TO_CHAR(DATE_TRUNC('week', CURRENT_DATE)::date, 'YYYY-MM-DD'),
   TO_CHAR((DATE_TRUNC('week', CURRENT_DATE)::date + INTERVAL '6 days')::date, 'YYYY-MM-DD'),
   'active', (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 days');
