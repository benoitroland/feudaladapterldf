from ldf_adapter.utils import ObjectFactory
from ldf_adapter.notifier.email import EmailNotifierBuilder

# from ldf_adapter.notifier.courier import CourierNotifierBuilder


class NotificationServiceProvider(ObjectFactory):
    def get(self, notifier_type, **kwargs):
        """Returns a configured notifier of given type.

        Args:
            notifier_type (str): type of notifier to return. supported notifiers: email, courier
            **kwargs: additional arguments to pass to notifier builder.
        Returns:
            Notifier: configured notifier of given type.
        """
        return self.create(notifier_type, **kwargs)


notifiers = NotificationServiceProvider()
notifiers.register_builder("email", EmailNotifierBuilder())
# notifiers.register_builder("courier", CourierNotifierBuilder())
