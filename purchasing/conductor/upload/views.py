# -*- coding: utf-8 -*-

import os

from flask import (
    request, current_app, render_template,
    jsonify, redirect, url_for, flash, session
)
from werkzeug import secure_filename

from purchasing.database import db
from purchasing.data.contracts import ContractBase, ContractType
from purchasing.data.importer.costars import main as import_costars
from purchasing.decorators import requires_roles
from purchasing.conductor.forms import FileUploadForm, ContractUploadForm
from purchasing.conductor.util import upload_costars_contract

from purchasing.conductor.upload import blueprint

@blueprint.route('/costars', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def upload_costars():
    '''Uploads a new csv file with properly-formatted COSTARS data

    :status 200: Renders the
        :py:class:`~purchasing.conductor.forms.FileUploadForm`
    :status 302: Saves the uploaded file through the
        :py:class:`~purchasing.conductor.forms.FileUploadForm`
        and redirects to processing to upload the saved file
    '''
    form = FileUploadForm()
    if form.validate_on_submit():
        _file = request.files.get('upload')
        filename = secure_filename(_file.filename)
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER'), filename)
        try:
            _file.save(filepath)
        except IOError:
            # if the upload folder doesn't exist, create it then save
            os.mkdir(current_app.config.get('UPLOAD_FOLDER'))
            _file.save(filepath)

        session['filepath'] = filepath
        session['filename'] = filename

        return redirect(url_for(
            'conductor_uploads.process'
        ))
    else:
        return render_template('conductor/upload/upload_new.html', form=form)

@blueprint.route('/costars/processing')
@requires_roles('conductor', 'admin', 'superadmin')
def process():
    '''Push the filepath and filename into the template to do the upload via ajax

    :status 200: render the upload success template
    '''
    filepath = session.pop('filepath', None)
    filename = session.pop('filename', None)

    return render_template(
        'conductor/upload/upload_success.html', filepath=filepath, filename=filename, _delete=True
    )

@blueprint.route('/costars/_process', methods=['POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def process_costars_upload():
    '''Perform the costars upload on the saved file

    .. seealso::
        :ref:`costars-importer`

    :status 200: successful costars file read and upload
    :status 500: error reading costars file
    '''
    filepath = request.form.get('filepath')
    filename = request.form.get('filename')
    delete = request.form.get('_delete')

    try:
        import_costars(filepath, filename, None, None, None)

        if delete not in ['False', 'false', False]:
            os.remove(filepath)

        return jsonify({'status': 'success'}), 200

    except Exception, e:
        return jsonify({'status': 'error: {}'.format(e)}), 500

@blueprint.route('/costars/contracts', methods=['GET', 'POST'])
@requires_roles('conductor', 'admin', 'superadmin')
def costars_contract_upload():
    '''Upload a contract document pdf for costars

    Because the COSTARS website streams contract documents via POST requests
    instead having them live at some static endpoint, they are re-hosted in S3.

    :status 200: render the upload costars document template
    :status 302: attempt to upload a costars document to S3 and set the
        ``contract_href`` on the relevant
        :py:class:`~purchasing.data.contracts.ContractBase` object. Redirect
        to the same page.
    '''
    contracts = ContractBase.query.join(ContractType).filter(
        db.func.lower(ContractType.name) == 'costars',
        db.or_(
            ContractBase.contract_href == None,
            ContractBase.contract_href == ''
        )
    ).all()

    form = ContractUploadForm()

    if form.validate_on_submit():
        _file = request.files.get('upload')
        filename, filepath = upload_costars_contract(_file)

        contract = ContractBase.query.get(int(form.data.get('contract_id')))

        contract.update(contract_href=filepath)
        flash('Contract uploaded successfully', 'alert-success')
        return redirect(url_for('conductor_uploads.costars_contract_upload'))

    return render_template(
        '/conductor/upload/upload_costars_documents.html',
        form=form, contracts=contracts
    )
