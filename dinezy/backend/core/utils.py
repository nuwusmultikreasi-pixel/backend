import io

from django.template.loader import get_template


def generate_pdf(template_src, context_dict=None):
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return None
    html = get_template(template_src).render(context_dict or {})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None
