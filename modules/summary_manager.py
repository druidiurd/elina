from datetime import datetime, timedelta

class SummaryManager:
    @staticmethod
    def get_period_dates(period: str):
        today = datetime.now().date()
        if period == "day":
            return today, today
        elif period == "week":
            start = today - timedelta(days=today.weekday())
            end = today
            return start, end
        else:
            raise ValueError("Unknown period")

    @staticmethod
    def get_summary(user_id: str, db, period: str = "day"):
        start_date, end_date = SummaryManager.get_period_dates(period)
        activities_ref = db.collection('activities')
        query = activities_ref.where('user_id', '==', user_id)
        docs = query.stream()

        summary = {}
        total = 0
        for doc in docs:
            data = doc.to_dict()
            act_date = datetime.strptime(data.get('date'), "%Y-%m-%d").date()
            if start_date <= act_date <= end_date:
                act_type = data.get('type', 'other')
                summary[act_type] = summary.get(act_type, 0) + 1
                total += 1

        return summary, total, start_date, end_date

    @staticmethod
    def format_summary(summary, total, start_date, end_date):
        if total == 0:
            return "За цей період не було жодної активності."
        period_str = f"{start_date.strftime('%d.%m.%Y')}"
        if start_date != end_date:
            period_str += f" – {end_date.strftime('%d.%m.%Y')}"
        lines = [f"Підсумок за {period_str}:", f"Всього активностей: {total}"]
        emoji = {
            "meal": "🍽",
            "exercise": "💪",
            "sleep": "😴",
            "work": "🏢",
            "rest": "🛋",
            "drink": "💧",
            "cleaning": "🧹",
            "meeting": "👥",
            "other": "❓"
        }
        for act_type, count in summary.items():
            lines.append(f"{emoji.get(act_type, '❓')} {act_type}: {count}")
        return "\n".join(lines)
