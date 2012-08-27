#This file is part account_invoice_consecutive module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import Workflow, ModelView, ModelSQL
from trytond.transaction import Transaction
from trytond.pool import Pool


class Invoice(Workflow, ModelSQL, ModelView):
    _name = 'account.invoice'

    def __init__(self):
        super(Invoice, self).__init__()
        self._error_messages.update({
                'invalid_number_date': 'You are trying to create invoice '
                    '%(invoice_number)s with date %(invoice_date)s but '
                    '%(invoice_count)d invoices exist which have incompatible '
                    'numbers and dates:\n\n%(invoices)s',
                'invalid_number_date_item': 'Number: %(number)s\nDate: '
                    '%(date)s\n',
                })

    def set_number(self, invoice):
        pool = Pool()
        res = super(Invoice, self).set_number(invoice)
        # TODO: When do we check this?
        #if not invoice.journal_id.check_invoice_lines_tax:
            #continue
        if invoice.type in ('out_invoice', 'out_credit_note'):
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
                """, (invoice.type, invoice.number, invoice.invoice_date, 
                    invoice.number, invoice.invoice_date))
            records = cursor.fetchall()
            if records:
                limit = 5
                language = Transaction().language
                lang_obj = pool.get('ir.lang')
                lang_id, = lang_obj.search([('code', '=', language)])
                lang = lang_obj.browse(lang_id)
                error = self._error_messages['invalid_number_date_item']
                translation_obj = pool.get('ir.translation')
                message = translation_obj.get_source('account.invoice', 
                    'error', language, error)
                if not message:
                    message = translation_obj.get_source(error, 'error', 
                        language)
                if message:
                    error = message
                text = []
                records = [error % {
                        'number': record[0],
                        'date': lang_obj.strftime(record[1], lang.code, 
                            lang.date),
                        } for record in records]
                text = '\n'.join(records[:limit])
                self.raise_user_error('invalid_number_date', {
                        'invoice_number': invoice.number, 
                        'invoice_date': lang_obj.strftime(invoice.invoice_date,
                            lang.code, lang.date), 
                        'invoice_count': len(records),
                        'invoices': text,
                        })
        return res

Invoice()
