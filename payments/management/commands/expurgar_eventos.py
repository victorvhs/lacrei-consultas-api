import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from payments.models import EventoRecebido

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Expurga eventos recebidos com mais de 90 dias"

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=90, help="Dias para expurgo")

    def handle(self, *args, **options):
        dias = options["dias"]
        cutoff = timezone.now() - timedelta(days=dias)

        count, _ = EventoRecebido.objects.filter(recebido_em__lt=cutoff).delete()

        self.stdout.write(self.style.SUCCESS(f"Expurgo concluido: {count} eventos removidos."))
