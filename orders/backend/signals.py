from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import Signal, receiver

from backend.models import ConfirmEmailToken


new_user_registered = Signal(
    # providing_args=['user_id'],
)


@receiver(new_user_registered)
def new_user_registered_signal(user_id, **kwargs):
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    msg = EmailMultiAlternatives(
        f'Confirm email token for {token.user.email}',
        token.key,
        settings.EMAIL_HOST_USER,
        [token.user.email]
    )
    msg.send()