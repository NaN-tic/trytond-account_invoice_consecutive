#This file is part account_invoice_consecutive module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import Workflow, ModelView, ModelSQL
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
                    '%(invoice_number)s invoice, date %(invoice_date)s. '
                    'There are %(invoice_count)d invoices before this date:'
                    '\n\n%(invoices)s',
                })

    def set_number(self):
        # TODO: When do we check this?
        #if not invoice.journal_id.check_invoice_lines_tax:
            #continue
        if self.type in ('out_invoice', 'out_credit_note'):
            res = super(Invoice, self).set_number()
            cursor = Transaction().cursor
            cursor.execute("""
                SELECT 
                    number, 
                    invoice_date
                FROM
                    account_invoice
                WHERE
                    type = %s AND (
                    (number < %s AND invoice_date > %s) OR
                    (number > %s AND invoice_date < %s)
                    )
                """, (self.type, self.number, self.invoice_date, 
                    self.number, self.invoice_date))
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
