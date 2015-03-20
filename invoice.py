#This file is part account_invoice_consecutive module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta

__all__ = ['Invoice']
__metaclass__ = PoolMeta


class Invoice:
    'Invoice'
    __name__ = 'account.invoice'

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._error_messages.update({
                'invalid_number_date': 'You are trying to create '
                    '%(invoice_number)s invoice on date %(invoice_date)s. '
                    'There are %(invoice_count)d invoices after this date:'
                    '\n\n%(invoices)s',
                })

    def set_number(self):
        # TODO: When do we check this?
        #if not invoice.journal_id.check_invoice_lines_tax:
            #continue
        pool = Pool()
        Period = pool.get('account.period')
        Move = pool.get('account.move')
        Lang = pool.get('ir.lang')
        Module = pool.get('ir.module.module')

        super(Invoice, self).set_number()
        if self.type in ('out_invoice', 'out_credit_note'):
            table = self.__table__()
            move = Move.__table__()
            accounting_date = self.accounting_date or self.invoice_date
            period_id = Period.find(self.company.id, date=accounting_date)
            query = table.join(move, condition=(table.move == move.id))
            where = ((table.state != 'draft') &
                (table.type == self.type) &
                (table.company == self.company.id) &
                (move.period == period_id))

            account_invoice_sequence_module_installed = Module.search([
                    ('name', '=', 'account_invoice_multisequence'),
                    ('state', '=', 'installed'),
                ])
            if account_invoice_sequence_module_installed:
                where &= (table.journal == self.journal.id)

            where &= (((table.number < self.number) &
                    (table.invoice_date > accounting_date)) |
                ((table.number > self.number) &
                    (table.invoice_date < accounting_date)))
            query = query.select(table.number, table.invoice_date, where=where)
            cursor = Transaction().cursor
            cursor.execute(*query)
            records = cursor.fetchall()
            if records:
                language = Transaction().language
                languages = Lang.search([('code', '=', language)])
                if not languages:
                    languages = Lang.search([('code', '=', 'en_US')])
                language = languages[0]
                limit = 5
                info = ['%(number)s - %(date)s' % {
                    'number': record[0],
                    'date': Lang.strftime(record[1], language.code,
                        language.date),
                    } for record in records]
                info = '\n'.join(info[:limit])
                self.raise_user_error('invalid_number_date', {
                    'invoice_number': self.number,
                    'invoice_date': Lang.strftime(self.invoice_date,
                        language.code, language.date),
                    'invoice_count': len(records),
                    'invoices': info,
                    })
