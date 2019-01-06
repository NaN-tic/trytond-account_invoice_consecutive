# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from sql.aggregate import Sum
from sql.functions import Round
from trytond.i18n import gettext
from trytond.exceptions import UserError
__all__ = ['Invoice']


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def validate(cls, invoices):
        super(Invoice, cls).validate(invoices)
        for invoice in invoices:
            if invoice.type != 'in':
                invoice.check_same_dates()

    def check_same_dates(self):
        pool = Pool()
        Lang = pool.get('ir.lang')

        if (self.invoice_date and self.accounting_date
                and self.invoice_date != self.accounting_date):
            language = Transaction().language
            languages = Lang.search([('code', '=', language)], limit=1)
            if not languages:
                languages = Lang.search([('code', '=', 'en')], limit=1)
            language, = languages

            raise UserError(gettext(
                'account_invoice_consecutive.not_same_dates',
                    invoice_date'=Lang.strftime(self.invoice_date,
                        language.code, language.date),
                    accounting_date= Lang.strftime(self.accounting_date,
                        language.code, language.date)))

    @classmethod
    def set_number(cls, invoices):
        # TODO: When do we check this?
        # if not invoice.journal_id.check_invoice_lines_tax:
            # continue
        pool = Pool()
        Period = pool.get('account.period')
        Lang = pool.get('ir.lang')
        Module = pool.get('ir.module')
        Inv = pool.get('account.invoice')

        to_check = [i for i in invoices if i.type == 'out' and not i.number]

        super(Invoice, cls).set_number(invoices)
        for invoice in to_check:
            # As we have a control in the validate that make the
            # accounting_date have to be the same as invoice_date, in cas it
            # exist, we can use invoice_date to calculate the period.
            period_id = Period.find(
                invoice.company.id, date=invoice.invoice_date)
            fiscalyear = Period(period_id).fiscalyear

            domain = [
                ('number', '!=', None),
                ('type', '=', invoice.type),
                ('company', '=', invoice.company.id),
                ('move.period.fiscalyear', '=', fiscalyear.id),
                ['OR', [
                        ('number', '<', invoice.number),
                        ('invoice_date', '>', invoice.invoice_date),
                        ], [
                        ('number', '>', invoice.number),
                        ('invoice_date', '<', invoice.invoice_date),
                        ],],
                ]

            if invoice.untaxed_amount >= 0:
                domain.append(('untaxed_amount', '>=', 0))
            else:
                domain.append(('untaxed_amount', '<', 0))

            account_invoice_sequence_module_installed = Module.search([
                    ('name', '=', 'account_invoice_multisequence'),
                    ('state', '=', 'activated'),
            ])

            if account_invoice_sequence_module_installed:
                domain.append(('journal', '=', invoice.journal.id))

            invs = Inv.search(domain, limit=5)

            if invs:
                language = Lang.get()
                info = ['%(number)s - %(date)s' % {
                    'number': inv.number,
                    'date': language.strftime(inv.invoice_date),
                    } for inv in invs]
                info = '\n'.join(info)
                raise UserError(gettext(
                    'account_invoice_consecutiveinvalid_number_date',
                        invoice_number=invoice.number,
                        invoice_date=language.strftime(invoice.invoice_date),
                        invoice_count=len(invs),
                        invoices=info))
