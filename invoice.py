#This file is part account_invoice_consecutive module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.transaction import Transaction
from trytond.pool import PoolMeta

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
                    '%(invoice_number)s invoice, date %(invoice_date)s. '
                    'There are %(invoice_count)d invoices before this date:'
                    '\n\n%(invoices)s',
                })

    def set_number(self):
        # TODO: When do we check this?
        #if not invoice.journal_id.check_invoice_lines_tax:
            #continue
        super(Invoice, self).set_number()
        if self.type in ('out_invoice', 'out_credit_note'):
            table = self.__table__()
            query = table.select(table.number, table.invoice_date,
                where=((table.state != 'draft') &
                    (table.type == self.type) &
                    (table.company == self.company.id) &
                    (((table.number < self.number) &
                            (table.invoice_date > self.invoice_date)) |
                        ((table.number > self.number) &
                                (table.invoice_date < self.invoice_date)))))
            cursor = Transaction().cursor
            cursor.execute(*query)
            records = cursor.fetchall()
            if records:
                limit = 5
                info = ['%(number)s - %(date)s' % {
                    'number': record[0],
                    'date': unicode(record[1]),
                    } for record in records]
                info = '\n'.join(info[:limit])
                self.raise_user_error('invalid_number_date', {
                    'invoice_number': self.number,
                    'invoice_date': self.invoice_date,
                    'invoice_count': len(records),
                    'invoices': info,
                    })
