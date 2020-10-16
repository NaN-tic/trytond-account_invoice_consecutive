# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.model import fields
from sql.aggregate import Sum
from sql.functions import Round
from trytond.i18n import gettext
from trytond.exceptions import UserError
__all__ = ['Invoice']


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    sequence = fields.Many2One('ir.sequence.strict', "Sequence", readonly=True)

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
                    invoice_date=Lang.strftime(self.invoice_date,
                        language.code, language.date),
                    accounting_date= Lang.strftime(self.accounting_date,
                        language.code, language.date)))

    def get_next_number(self, pattern=None):
        pool = Pool()
        Sequence = pool.get('ir.sequence.strict')
        Period = pool.get('account.period')

        if pattern is None:
            pattern = {}
        else:
            pattern = pattern.copy()

        accounting_date = self.accounting_date or self.invoice_date
        period_id = Period.find(
            self.company.id, date=accounting_date,
            test_state=self.type != 'in')

        period = Period(period_id)
        fiscalyear = period.fiscalyear
        pattern.setdefault('company', self.company.id)
        pattern.setdefault('fiscalyear', fiscalyear.id)
        pattern.setdefault('period', period.id)
        invoice_type = self.type
        invoice_type += self.invoice_type_criteria()

        for invoice_sequence in fiscalyear.invoice_sequences:
            if invoice_sequence.match(pattern):
                sequence = getattr(
                    invoice_sequence, '%s_sequence' % invoice_type)
                break
        else:
            raise InvoiceNumberError(
                gettext('account_invoice.msg_invoice_no_sequence',
                    invoice=self.rec_name,
                    fiscalyear=fiscalyear.rec_name))
        with Transaction().set_context(date=accounting_date):
            if Transaction().context.get('check_consecutive'):
                return Sequence.get_id(sequence.id), sequence
            return Sequence.get_id(sequence.id)

    @classmethod
    def set_number(cls, invoices):
        '''
        Set number to the invoice
        '''
        pool = Pool()
        Date = pool.get('ir.date')
        Lang = pool.get('ir.lang')
        Period = pool.get('account.period')
        Module = pool.get('ir.module')
        today = Date.today()

        def accounting_date(invoice):
            return invoice.accounting_date or invoice.invoice_date or today

        invoices = sorted(invoices, key=accounting_date)
        sequences = set()

        super(Invoice, cls).set_number(invoices)
        for invoice in invoices:
            # Posted and paid invoices are tested by check_modify so we can
            # not modify tax_identifier nor number
            if invoice.state in {'posted', 'paid'}:
                continue
            if not invoice.tax_identifier:
                invoice.tax_identifier = invoice.get_tax_identifier()
            # Generated invoice may not fill the party tax identifier
            if not invoice.party_tax_identifier:
                invoice.party_tax_identifier = invoice.party.tax_identifier

            if invoice.number:
                continue

            if not invoice.invoice_date and invoice.type == 'out':
                invoice.invoice_date = today
            with Transaction().set_context(check_consecutive=True):
                invoice.number, invoice.sequence = invoice.get_next_number()
            if invoice.type == 'out' and invoice.sequence not in sequences:
                date = accounting_date(invoice)
                period_id = Period.find(
                    invoice.company.id, date=invoice.invoice_date)
                fiscalyear = Period(period_id).fiscalyear
                # Do not need to lock the table
                # because sequence.get_id is sequential
                domain = [
                    ('sequence', '=', invoice.sequence.id),
                    ('move.period.fiscalyear', '=', fiscalyear.id),
                    ['OR', [
                            ('number', '<', invoice.number),
                            ('invoice_date', '>', invoice.invoice_date),
                            ], [
                            ('number', '>', invoice.number),
                            ('invoice_date', '<', invoice.invoice_date),
                            ],],
                    ]

                account_invoice_sequence_module_installed = Module.search([
                        ('name', '=', 'account_invoice_multisequence'),
                        ('state', '=', 'activated'),
                ])

                if account_invoice_sequence_module_installed:
                    domain.append(('journal', '=', invoice.journal.id))

                after_invoices = cls.search(domain, limit=5)

                if after_invoices:
                    language = Lang.get()
                    info = ['%(number)s - %(date)s' % {
                        'number': after_invoice.number,
                        'date': language.strftime(after_invoice.invoice_date),
                        } for after_invoice in after_invoices]
                    info = '\n'.join(info)
                    raise UserError(gettext(
                        'account_invoice_consecutive.invalid_number_date',
                            invoice_number=invoice.number,
                            invoice_date=language.strftime(invoice.invoice_date),
                            invoice_count=len(after_invoices),
                            invoices=info))
                sequences.add(invoice.sequence)
        cls.save(invoices)
