# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta

__all__ = ['Invoice']


class Invoice:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice'

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._error_messages.update({
                'invalid_number_date': 'You are trying to create '
                    '%(invoice_number)s invoice on date %(invoice_date)s. '
                    'There are %(invoice_count)d invoices after this date:'
                    '\n\n%(invoices)s',
                'not_same_dates': 'You are trying to validate an invoice '
                    'where invoice date (%(invoice_date)s) and accounting '
                    'date (%(accounting_date)s) are different. That is not '
                    'permitted, because of invoice number and date '
                    'correlation.',
                })

    @classmethod
    def validate(cls, invoices):
        super(Invoice, cls).validate(invoices)
        for invoice in invoices:
            if invoice.type != 'in':
                invoice.check_same_dates()

    def check_same_dates(self):
        pool=Pool()
        Lang = pool.get('ir.lang')

        if (self.invoice_date and self.accounting_date
            and self.invoice_date != self.accounting_date):
            language = Transaction().language
            languages = Lang.search([('code', '=', language)])
            if not languages:
                languages = Lang.search([('code', '=', 'en_US')])
            language = languages[0]

            self.raise_user_error('not_same_dates', {
                'invoice_date': Lang.strftime(self.invoice_date, language.code,
                    language.date),
                'accounting_date': Lang.strftime(self.accounting_date,
                    language.code, language.date),
                })

    def set_number(self):
        # TODO: When do we check this?
        # if not invoice.journal_id.check_invoice_lines_tax:
            # continue
        pool = Pool()
        Period = pool.get('account.period')
        Lang = pool.get('ir.lang')
        Module = pool.get('ir.module')
        Inv = pool.get('account.invoice')

        has_number = True if self.number else False
        super(Invoice, self).set_number()
        if self.type == 'out' and not has_number:
            # As we have a control in the validate that make the
            # accounting_date have to be the same as invoice_date, in cas it
            # exist, we can use invoice_date to calculate the period.
            period_id = Period.find(self.company.id, date=self.invoice_date)
            fiscalyear = Period(period_id).fiscalyear

            domain = [
                ('number', '!=', None),
                ('type', '=', self.type),
                ('company', '=', self.company.id),
                ('move.period.fiscalyear', '=', fiscalyear.id),
                ['OR', [
                        ('number', '<', self.number),
                        ('invoice_date', '>', self.invoice_date),
                        ], [
                        ('number', '>', self.number),
                        ('invoice_date', '<', self.invoice_date),
                        ],],
                ]

            if self.untaxed_amount >= 0:
                domain.append(('untaxed_amount', '>=', 0))
            else:
                domain.append(('untaxed_amount', '<', 0))

            account_invoice_sequence_module_installed = Module.search([
                    ('name', '=', 'account_invoice_multisequence'),
                    ('state', '=', 'installed'),
                ])
            if account_invoice_sequence_module_installed:
                domain.append(('journal', '=', self.journal.id))

            invoices = Inv.search(domain, limit=5)

            if invoices:
                language = Transaction().language
                languages = Lang.search([('code', '=', language)])
                if not languages:
                    languages = Lang.search([('code', '=', 'en_US')])
                language = languages[0]
                info = ['%(number)s - %(date)s' % {
                    'number': invoice.number,
                    'date': Lang.strftime(invoice.invoice_date, language.code,
                        language.date),
                    } for invoice in invoices]
                info = '\n'.join(info)
                self.raise_user_error('invalid_number_date', {
                    'invoice_number': self.number,
                    'invoice_date': Lang.strftime(self.invoice_date,
                        language.code, language.date),
                    'invoice_count': len(invoices),
                    'invoices': info,
                    })
