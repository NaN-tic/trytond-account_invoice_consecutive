# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
try:
    from trytond.modules.account_invoice_consecutive.tests.test_account_invoice_consecutive import suite
except ImportError:
    from .test_account_invoice_consecutive import suite

__all__ = ['suite']
