# This file is part of the account_invoice_consecutive module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import unittest
from trytond.pool import Pool
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.exceptions import UserError

from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart, get_fiscalyear
from trytond.modules.account_invoice.tests import set_invoice_sequences


class AccountInvoiceConsecutiveTestCase(ModuleTestCase):
    'Test Account Invoice Consecutive module'
    module = 'account_invoice_consecutive'

    @with_transaction()
    def test0010check_invoice_date(self):
        'Test check_credit_limit'
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
        Account = pool.get('account.account')
        Invoice = pool.get('account.invoice')
        Journal = pool.get('account.journal')
        Party = pool.get('party.party')
        PaymentTerm = pool.get('account.invoice.payment_term')

        company = create_company()
        with set_company(company):
            create_chart(company)
            fiscalyear = set_invoice_sequences(get_fiscalyear(company))
            fiscalyear.save()
            FiscalYear.create_period([fiscalyear])
            first_period = fiscalyear.periods[0]
            second_period = fiscalyear.periods[1]

            receivable, = Account.search([
                    ('type.receivable', '=', True),
                    ])
            revenue, = Account.search([
                    ('type.revenue', '=', True),
                    ])
            account_tax, = Account.search([
                    ('name', '=', 'Main Tax'),
                    ])
            journal, = Journal.search([], limit=1)

            party, = Party.create([{
                        'name': 'Party',
                        'addresses': [('create', [{}])],
                        'account_receivable': receivable.id,
                        }])

            term, = PaymentTerm.create([{
                        'name': 'Payment term',
                        'lines': [
                            ('create', [{
                                        'type': 'remainder',
                                        'relativedeltas': [
                                            ('create', [{
                                                        'sequence': 0,
                                                        'days': 0,
                                                        'months': 0,
                                                        'weeks': 0,
                                                        }])],
                                        }])],
                        }])

            def create_invoice(date):
                invoice, = Invoice.create([{
                        'invoice_date': date,
                        'type': 'out',
                        'party': party.id,
                        'invoice_address': party.addresses[0].id,
                        'journal': journal.id,
                        'account': receivable.id,
                        'payment_term': term.id,
                        'lines': [
                            ('create', [{
                                        'invoice_type': 'out',
                                        'type': 'line',
                                        'sequence': 0,
                                        'description': 'invoice_line',
                                        'account': revenue.id,
                                        'quantity': 1,
                                        'unit_price': Decimal('50.0'),
                                        }])],
                        }])
                Invoice.post([invoice])
                return invoice
            today = second_period.start_date + relativedelta(days=2)
            yesterday = second_period.start_date + relativedelta(days=1)
            create_invoice(today)
            # Invoices can be created in the past
            error_msg = 'There are 1 invoices after this date'
            for date in [yesterday, first_period.end_date,
                    first_period.start_date]:
                with self.assertRaises(UserError) as cm:
                    create_invoice(yesterday)
                self.assertTrue(error_msg in cm.exception.message)
            # Invoices can be created in the future
            create_invoice(today + relativedelta(days=1))
            create_invoice(today + relativedelta(days=2))


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountInvoiceConsecutiveTestCase))
    return suite
