from bson import ObjectId
from bson.errors import InvalidId
from django.core.management.base import BaseCommand, CommandError

from ...models import Comparison
from ...services.comparisons import process_comparison

#All of this is basically so I can run the comparison processing code in a separate process
#This process will be called by the background worker
#The process can be capped by the worker so it closes within a certain time

class Command(BaseCommand):
    help = "Process one comparison already claimed by the worker."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("comparison_id")
        parser.add_argument("attempt", type=int)

    def handle(self, *args, comparison_id, attempt, **options):
        try:
            comparison_id = ObjectId(comparison_id)
        except InvalidId as error:
            raise CommandError("Invalid comparison ID.") from error

        try:
            #Run the comparison! 
            process_comparison(
                comparison_id,
                claimed_attempt=attempt,
            )
        except Comparison.DoesNotExist:
            return