#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name': 'Account Invoice Consecutive',
    'version': '2.3.0',
    'author': 'NaN·tic',
    'email': 'info@NaN-tic.com',
    'website': 'http://www.tryton.org/',
    'description': 'Allows ensuring new invoices do not have a date previous '\
        'to the latest invoice in the sequence, as required by the law of '\
        'some countries such as Spain.',
    'depends': [
        'ir',
        'account',
        'company',
        'party',
        'product',
        'res',
        'currency',
        'account_product',
        'account_invoice',
        ],
    'xml': [
        ],
    'translation': [
        ]
}
