from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import Signal, receiver

from backend.models import ConfirmEmailToken, User

new_user_registered = Signal()

new_order = Signal()


@receiver(new_user_registered)
def new_user_registered_signal(user_id, **kwargs):
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    msg = EmailMultiAlternatives(
        f'Confirm email token for {token.user.email}',
        f'{token.key}',
        settings.EMAIL_HOST_USER,
        [token.user.email]
    )
    msg.send()


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    user = User.objects.filter(id=user_id).first()

    msg = EmailMultiAlternatives(
        'Новый статус заказа',
        'Заказ передан поставщику',
        settings.EMAIL_HOST_USER,
        [user.email]
    )
    msg.send()
