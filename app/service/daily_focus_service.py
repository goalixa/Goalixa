from datetime import date, datetime
from typing import Optional


class DailyFocusService:
    """Service for managing daily focus (per-user, per-day task focus lists)."""

    def __init__(self, repository):
        """Initialize DailyFocusService with a repository instance.

        Args:
            repository: PostgresRepository instance for data access
        """
        self.repository = repository

    def get_focus(self, user_id: int, focus_date: Optional[date] = None) -> dict:
        """Get daily focus list for a specific user and date.

        If focus_date is None, uses today's date. Returns empty focus if not found.

        Args:
            user_id: The user ID (for authorization context)
            focus_date: Target date (defaults to today)

        Returns:
            dict: Focus list data from repository
        """
        if focus_date is None:
            focus_date = date.today()
        try:
            return self.repository.get_daily_focus(focus_date)
        except Exception:
            # Return empty focus if not found
            return {"date": focus_date.isoformat(), "items": []}

    def add_tasks(
        self,
        user_id: int,
        focus_date: date,
        task_ids: list,
        time_block: str = 'unscheduled'
    ) -> dict:
        """Add tasks to daily focus.

        Validates that time_block is valid and task_ids is a non-empty list.
        All tasks must belong to the user (verified by repository).

        Args:
            user_id: The user ID (for authorization)
            focus_date: Target date
            task_ids: List of task IDs to add
            time_block: Time block category (morning, afternoon, evening, unscheduled)

        Returns:
            dict: Updated focus list

        Raises:
            ValueError: If time_block is invalid or task_ids is invalid/empty
        """
        # Validate time_block
        valid_blocks = ['morning', 'afternoon', 'evening', 'unscheduled']
        if time_block not in valid_blocks:
            raise ValueError(f"Invalid time_block. Must be one of: {valid_blocks}")

        # Validate task_ids is a list
        if not isinstance(task_ids, list):
            raise ValueError("task_ids must be a list")

        # Validate task_ids is not empty
        if not task_ids:
            raise ValueError("task_ids cannot be empty")

        # Add to focus (repository will validate task ownership)
        return self.repository.add_to_daily_focus(focus_date, task_ids, time_block)

    def reorder(self, user_id: int, focus_date: date, items: list) -> dict:
        """Reorder focus items with validation.

        Validates items format and position sequencing.

        Args:
            user_id: The user ID (for authorization)
            focus_date: Target date
            items: List of items with {id, time_block, position}

        Returns:
            dict: Updated focus list

        Raises:
            ValueError: If items format is invalid or positions are not sequential
        """
        # Validate items is a list
        if not isinstance(items, list):
            raise ValueError("items must be a list")

        # Validate each item has required fields
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each item must be a dictionary")
            if 'id' not in item or 'time_block' not in item or 'position' not in item:
                raise ValueError("Each item must have: id, time_block, position")

        # Validate time_block values
        valid_blocks = ['morning', 'afternoon', 'evening', 'unscheduled']
        for item in items:
            if item['time_block'] not in valid_blocks:
                raise ValueError(f"Invalid time_block: {item['time_block']}")

        # Validate positions are sequential per time_block
        positions_by_block = {}
        for item in items:
            block = item['time_block']
            pos = item['position']
            if block not in positions_by_block:
                positions_by_block[block] = []
            positions_by_block[block].append(pos)

        for block, positions in positions_by_block.items():
            sorted_pos = sorted(positions)
            if sorted_pos != list(range(len(sorted_pos))):
                raise ValueError(f"Positions for {block} must be sequential starting at 0")

        return self.repository.reorder_daily_focus(focus_date, items)

    def update_item(self, user_id: int, item_id: int, updates: dict) -> dict:
        """Update a single focus item with validation.

        Only allows updating: time_block, scheduled_start, scheduled_end.
        Validates time_block if provided and scheduled times make sense.

        Args:
            user_id: The user ID (for authorization)
            item_id: The focus item ID to update
            updates: Dictionary with fields to update

        Returns:
            dict: Updated focus list

        Raises:
            ValueError: If updates contain invalid fields or invalid values
            PermissionError: If item doesn't exist or user is unauthorized
        """
        # Only allow specific fields
        allowed_fields = ['time_block', 'scheduled_start', 'scheduled_end']
        filtered = {k: v for k, v in updates.items() if k in allowed_fields}

        # Validate time_block if provided
        if 'time_block' in filtered:
            valid_blocks = ['morning', 'afternoon', 'evening', 'unscheduled']
            if filtered['time_block'] not in valid_blocks:
                raise ValueError(f"Invalid time_block: {filtered['time_block']}")

        # Validate scheduled times make sense
        if 'scheduled_start' in filtered and 'scheduled_end' in filtered:
            start = filtered['scheduled_start']
            end = filtered['scheduled_end']
            if start and end and start >= end:
                raise ValueError("scheduled_start must be before scheduled_end")

        result = self.repository.update_daily_focus_item(item_id, filtered)
        if not result:
            raise PermissionError("Item not found or unauthorized")
        return result

    def remove_task(self, user_id: int, item_id: int) -> bool:
        """Remove task from daily focus.

        Args:
            user_id: The user ID (for authorization)
            item_id: The focus item ID to remove

        Returns:
            bool: True if successful

        Raises:
            PermissionError: If item doesn't exist or user is unauthorized
        """
        result = self.repository.remove_from_daily_focus(item_id)
        if not result:
            raise PermissionError("Item not found or unauthorized")
        return result

    def complete_task(self, user_id: int, item_id: int) -> dict:
        """Mark a focus item as complete.

        Args:
            user_id: The user ID (for authorization)
            item_id: The focus item ID to mark complete

        Returns:
            dict: Updated focus list

        Raises:
            PermissionError: If item doesn't exist or user is unauthorized
        """
        result = self.repository.complete_daily_focus_item(item_id)
        if not result:
            raise PermissionError("Item not found or unauthorized")
        return result

    def auto_fill(
        self,
        user_id: int,
        focus_date: date,
        max_tasks: int = 5,
        priority: str = 'high'
    ) -> dict:
        """Auto-fill focus list with high-priority tasks.

        Args:
            user_id: The user ID (for authorization)
            focus_date: Target date
            max_tasks: Maximum number of tasks to add
            priority: Priority level (high, medium, low)

        Returns:
            dict: Updated focus list

        Raises:
            ValueError: If max_tasks <= 0 or priority is invalid
        """
        if max_tasks < 1:
            raise ValueError("max_tasks must be at least 1")
        if priority not in ['high', 'medium', 'low']:
            raise ValueError("priority must be one of: high, medium, low")

        return self.repository.auto_fill_daily_focus(focus_date, max_tasks, priority)

    def carry_over(self, user_id: int, from_date: date, to_date: date) -> dict:
        """Carry over incomplete tasks from one date to another.

        Args:
            user_id: The user ID (for authorization)
            from_date: Source date
            to_date: Target date (must be after from_date)

        Returns:
            dict: Updated focus list for to_date

        Raises:
            ValueError: If to_date is not after from_date
        """
        if to_date <= from_date:
            raise ValueError("to_date must be after from_date")
        return self.repository.carry_over_daily_focus(from_date, to_date)
