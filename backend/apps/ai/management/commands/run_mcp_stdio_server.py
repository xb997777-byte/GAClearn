from django.core.management.base import BaseCommand

from apps.ai.mcp.stdio_server import run_stdio_server


class Command(BaseCommand):
    help = "Run the standalone MCP server over STDIO."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting MCP STDIO server..."))
        run_stdio_server()
