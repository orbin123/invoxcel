from django.core.management.base import BaseCommand, CommandError

from services.azure_document_intelligence import AzureInvoiceClient, ExtractionError


class Command(BaseCommand):
    help = "Check Azure authentication with a read-only request; no invoice is uploaded."

    def handle(self, *args, **options):
        try:
            AzureInvoiceClient().check_connection()
        except ExtractionError as exc:
            details = ", ".join(f"{name}={value}" for name, value in exc.metadata.items())
            raise CommandError(f"{exc}" + (f" ({details})" if details else "")) from None
        self.stdout.write(self.style.SUCCESS("Azure authentication succeeded (HTTP 200). No invoice was uploaded. Restart Django after configuration changes."))
