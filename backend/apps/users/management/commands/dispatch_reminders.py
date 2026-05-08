from django.core.management.base import BaseCommand

from apps.users.reminders import dispatch_due_reminders


class Command(BaseCommand):
    help = "Dispatch or preview due mini-program reminder messages."

    def add_arguments(self, parser):
        parser.add_argument("--send", action="store_true", help="Actually send reminder messages")
        parser.add_argument("--tolerance", type=int, default=20, help="Reminder tolerance window in minutes")

    def handle(self, *args, **options):
        results = dispatch_due_reminders(
            dry_run=not options["send"],
            tolerance_minutes=options["tolerance"],
        )
        self.stdout.write(self.style.SUCCESS(f"processed reminders: {len(results)}"))
        for item in results:
            self.stdout.write(
                f"user={item['user_id']} status={item['status']} template={item['template_id']} page={item['page']}"
            )
