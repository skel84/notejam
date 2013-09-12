from pyramid.view import view_config, forbidden_view_config
from pyramid.renderers import get_renderer

from pyramid.security import remember, forget, authenticated_userid

from pyramid.httpexceptions import HTTPFound

from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer

from models import DBSession, User, Pad, Note
from forms import SignupSchema, SigninSchema, PadSchema, NoteSchema


@view_config(route_name='signin', renderer='templates/users/signin.pt')
@forbidden_view_config(renderer='templates/users/signin.pt')
def signin(request):
    form = Form(request, schema=SigninSchema())
    if form.validate():
        query = DBSession.query(User).filter(User.email == form.data['email'])
        if query.count():
            user = query.first()
            if user.check_password(form.data['password']):
                headers = remember(request, user.email)
                return HTTPFound(location='/', headers=headers)
            else:
                request.session.flash(u'Wrong email or password', 'error')
        else:
            request.session.flash(u'Wrong email or password', 'error')
    return _response_dict(
        request,
        renderer=FormRenderer(form),
    )


@view_config(route_name='signup', renderer='templates/users/signup.pt')
def signup(request):
    form = Form(request, schema=SignupSchema())
    if form.validate():
        user = form.bind(User())
        DBSession.add(user)
        request.session.flash(u'Now you can sign in', 'success')
        return HTTPFound(location=request.route_url('signin'))
    return _response_dict(request, renderer=FormRenderer(form))


@view_config(route_name='signout')
def signout(request):
    headers = forget(request)
    return HTTPFound(location=request.route_url('signin'), headers=headers)


def account_settings(request):
    pass


def forgot_password(request):
    pass


@view_config(route_name='notes', renderer='templates/notes/list.pt',
             permission='login_required')
def notes(request):
    notes = DBSession.query(Note).filter(
        Note.user == get_current_user(request)
    ).order_by(_get_order_by(request.params.get('order'))).all()
    return _response_dict(request, notes=notes)


@view_config(route_name='view_note', renderer='templates/notes/view.pt',
             permission='login_required')
def view_note(request):
    note_id = request.matchdict['note_id']
    note = DBSession.query(Note).filter(Note.id == note_id).first()
    return _response_dict(request, note=note)


@view_config(route_name='pad_notes', renderer='templates/pads/note_list.pt',
             permission='login_required')
def pad_notes(request):
    pad_id = request.matchdict['pad_id']
    pad = DBSession.query(Pad).filter(Pad.id == pad_id).first()
    return _response_dict(request, pad=pad)


@view_config(route_name='create_note', renderer='templates/notes/create.pt',
             permission='login_required')
def create_note(request):
    form = Form(request, schema=NoteSchema())
    if form.validate():
        note = form.bind(Note())
        note.user = get_current_user(request)
        DBSession.add(note)
        request.session.flash(u'Note is successfully created', 'success')
        return HTTPFound(location=request.route_url('notes'))
    return _response_dict(
        request,
        renderer=FormRenderer(form)
    )


@view_config(route_name='update_note', renderer='templates/notes/edit.pt',
             permission='login_required')
def update_note(request):
    note_id = request.matchdict['note_id']
    note = DBSession.query(Note).filter(Note.id == note_id).first()
    form = Form(request, schema=NoteSchema(), obj=note)
    if form.validate():
        note = form.bind(note)
        DBSession.add(note)
        request.session.flash(u'Note is successfully updated', 'success')

        # build redirect url
        location = request.route_url('notes')
        if note.pad is not None:
            location = request.route_url('pad_notes', pad_id=note.pad.id)

        return HTTPFound(location=location)
    return _response_dict(
        request,
        renderer=FormRenderer(form)
    )


@view_config(route_name='delete_note', renderer='templates/notes/delete.pt',
             permission='login_required')
def delete_note(request):
    note_id = request.matchdict['note_id']
    note = DBSession.query(Note).filter(Note.id == note_id).first()
    if request.method == 'POST':
        DBSession.delete(note)
        request.session.flash(u'Note is successfully deleted', 'success')
        return HTTPFound(location=request.route_url('notes'))
    return _response_dict(request, note=note)


@view_config(route_name='create_pad', renderer='templates/pads/create.pt',
             permission='login_required')
def create_pad(request):
    form = Form(request, schema=PadSchema())
    if form.validate():
        pad = form.bind(Pad())
        pad.user = get_current_user(request)
        DBSession.add(pad)
        request.session.flash(u'Pad is successfully created', 'success')
        return HTTPFound(location=request.route_url('notes'))
    return _response_dict(request, renderer=FormRenderer(form))


@view_config(route_name='update_pad', renderer='templates/pads/edit.pt',
             permission='login_required')
def update_pad(request):
    pad_id = request.matchdict['pad_id']
    pad = DBSession.query(Pad).filter(Pad.id == pad_id).first()
    form = Form(request, schema=PadSchema(), obj=pad)
    if form.validate():
        pad = form.bind(pad)
        pad.user = get_current_user(request)
        DBSession.add(pad)
        request.session.flash(u'Pad is successfully updated', 'success')
        return HTTPFound(
            location=request.route_url('pad_notes', pad_id=pad.id)
        )
    return _response_dict(request, renderer=FormRenderer(form), pad=pad)


@view_config(route_name='delete_pad', renderer='templates/pads/delete.pt',
             permission='login_required')
def delete_pad(request):
    pad_id = request.matchdict['pad_id']
    pad = DBSession.query(Pad).filter(Pad.id == pad_id).first()
    if request.method == 'POST':
        DBSession.delete(pad)
        request.session.flash(u'Pad is successfully deleted', 'success')
        return HTTPFound(location=request.route_url('notes'))
    return _response_dict(request, pad=pad)


#helper functions
def _response_dict(request, *args, **kwargs):
    return dict(
        logged_in=authenticated_userid(request),
        pads=DBSession.query(Pad).all(),
        snippets=get_renderer('templates/snippets.pt').implementation(),
        **kwargs
    )


def get_current_user(request):
    return DBSession.query(User).filter(
        User.email == authenticated_userid(request)
    ).first()


def _get_order_by(param='-updated_at'):
    ''' get model order param by string description '''
    return {
        'name': Note.name.asc(),
        '-name': Note.name.desc(),
        'updated_at': Note.updated_at.asc(),
        '-updated_at': Note.updated_at.desc(),
    }.get(param, Note.updated_at.desc())