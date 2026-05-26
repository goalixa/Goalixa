from datetime import date, datetime
from typing import Optional


class DailyFocusService:
    def __init__(self, repository):
        self.repo = repository

    def get_focus(self, focus_date: Optional[date] = None) -> dict:
        """Get daily focus list. Defaults to today."""
        if focus_date is None:
            focus_date = date.today()
        return self.repo.get_daily_focus(focus_date)

    def add_tasks(self, focus_date: date, task_ids: list, time_block: str = 'unscheduled') -> dict:
        """Add tasks to daily focus."""
        # Validate time_block
        valid_blocks = ['morning', 'afternoon', 'evening', 'unscheduled']
        if time_block not in valid_blocks:
            raise ValueError(f"Invalid time_block. Must be one of: {valid_blocks}")

        # Validate task_ids is a list
        if not isinstance(task_ids, list):
            raise ValueError("task_ids must be a list")

        # Add to focus
        return self.repo.add_to_daily_focus(focus_date, task_ids, time_block)

    def reorder(self, focus_date: date, items: list) -> dict:
        """Reorder focus items."""
        # Validate items is a list
        if not isinstance(items, list):
            raise ValueError("items must be a list")

        return self.repo.reorder_daily_focus(focus_date, items)

    def update_item(self, item_id: int, updates: dict) -> dict:
        """Update single focus item."""
        allowed_fields = ['time_block', 'scheduled_start', 'scheduled_end']
        filtered = {k: v for k, v in updates.items() if k in allowed_fields}
        return self.repo.update_daily_focus_item(item_id, filtered)

    def remove_task(self, item_id: int) -> bool:
        """Remove task from focus."""
        return self.repo.remove_from_daily_focus(item_id)

    def complete_task(self, item_id: int) -> dict:
        """Mark focus item complete."""
        return self.repo.complete_daily_focus_item(item_id)

    def auto_fill(self, focus_date: date, max_tasks: int = 5, priority: str = 'high') -> dict:
        """Auto-fill with high priority tasks."""
        if max_tasks < 1:
            raise ValueError("max_tasks must be at least 1")
        if priority not in ['high', 'medium', 'low']:
            raise ValueError("priority must be one of: high, medium, low")

        return self.repo.auto_fill_daily_focus(focus_date, max_tasks, priority)

    def carry_over(self, from_date: date, to_date: date) -> dict:
        """Carry over incomplete tasks."""
        if to_date <= from_date:
            raise ValueError("to_date must be after from_date")
        return self.repo.carry_over_daily_focus(from_date, to_date)
