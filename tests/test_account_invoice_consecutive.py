# This file is part of the account_invoice_consecutive module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import doctest
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction
from trytond.exceptions import UserError


class AccountInvoiceConsecutiveTestCase(ModuleTestCase):
    'Test Account Invoice Consecutive module'
    module = 'account_invoice_consecutive'

    def setUp(self):
        super(AccountInvoiceConsecutiveTestCase, self).setUp()
        self.account = POOL.get('account.account')
        self.invoice = POOL.get('account.invoice')
        self.journal = POOL.get('account.journal')
        self.field = POOL.get('ir.model.field')
        self.party = POOL.get('party.party')
        self.payment_term = POOL.get('account.invoice.payment_term')
        self.sequence_strict = POOL.get('ir.sequence.strict')
        self.period = POOL.get('account.period')
        self.property = POOL.get('ir.property')

    def test0010check_credit_limit(self):
        'Test check_credit_limit'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            receivable, = self.account.search([
                    ('kind', '=', 'receivable'),
                    ])
            revenue, = self.account.search([
                    ('kind', '=', 'revenue'),
                    ])
            account_tax, = self.account.search([
                    ('kind', '=', 'other'),
                    ('name', '=', 'Main Tax'),
                    ])
            journal, = self.journal.search([], limit=1)
            first_period, second_period = self.period.search([], limit=2)
            fiscalyear = first_period.fiscalyear

            invoice_seq = self.sequence_strict()
            invoice_seq.name = fiscalyear.name
            invoice_seq.code = 'account.invoice'
            invoice_seq.company = fiscalyear.company
            invoice_seq.save()
            fiscalyear.out_invoice_sequence = invoice_seq
            fiscalyear.in_invoice_sequence = invoice_seq
            fiscalyear.out_credit_note_sequence = invoice_seq
            fiscalyear.in_credit_note_sequence = invoice_seq
            fiscalyear.save()
            party, = self.party.create([{
                        'name': 'Party',
                        'addresses': [('create', [{}])],
                        'account_receivable': receivable.id,
                        }])

            term, = self.payment_term.create([{
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

            field, = self.field.search([
                    ('name', '=', 'account_revenue'),
                    ('model.model', '=', 'product.template'),
                    ])

            self.property.create([{
                        'value': 'account.account,%d' % revenue.id,
                        'field': field.id,
                        'res': None,
                        }])

            def create_invoice(date):
                invoice, = self.invoice.create([{
                            'invoice_date': date,
                            'type': 'out_invoice',
                            'party': party.id,
                            'invoice_address': party.addresses[0].id,
                            'journal': journal.id,
                            'account': receivable.id,
                            'payment_term': term.id,
                            'lines': [
                                ('create', [{
                                            'invoice_type': 'out_invoice',
                                            'type': 'line',
                                            'sequence': 0,
                                            'description': 'invoice_line',
                                            'account': revenue.id,
                                            'quantity': 1,
                                            'unit_price': Decimal('50.0'),
                            }])],
                            }])
                self.invoice.post([invoice])
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
    from trytond.modules.account.tests import test_account
    for test in test_account.suite():
        if test not in suite and not isinstance(test, doctest.DocTestCase):
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountInvoiceConsecutiveTestCase))
    return suite
