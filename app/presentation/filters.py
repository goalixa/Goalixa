def register_filters(app):
    @app.template_filter("format_seconds")
    def format_seconds(total_seconds):
        total_seconds = int(total_seconds or 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
