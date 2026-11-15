import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 40_000_000

EKSTENSI = {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp'}
MB = 1024 * 1024


def bersihkan_gambar(f, label='Gambar', maks_mb=2, maks_sisi=1600):
    if not f:
        raise ValidationError(f'{label} wajib diunggah.')
    if f.size > maks_mb * MB:
        raise ValidationError(f'Ukuran {label.lower()} maksimal {maks_mb} MB.')
    try:
        f.seek(0)
        with Image.open(f) as cek:
            fmt = cek.format
            cek.verify()
        f.seek(0)
        im = Image.open(f)
        im.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError) as e:
        raise ValidationError(f'{label} rusak atau bukan gambar yang valid.') from e
    if fmt not in EKSTENSI:
        raise ValidationError(f'Format {label.lower()} harus PNG, JPG, atau WEBP.')

    im = ImageOps.exif_transpose(im)
    im.thumbnail((maks_sisi, maks_sisi), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    if fmt == 'JPEG':
        im.convert('RGB').save(out, 'JPEG', quality=90, optimize=True)
    elif fmt == 'WEBP':
        im.save(out, 'WEBP', quality=90)
    else:
        if im.mode not in ('1', 'L', 'LA', 'P', 'RGB', 'RGBA'):
            im = im.convert('RGBA')
        im.save(out, 'PNG', optimize=True)
    return ContentFile(out.getvalue(), name=f'{uuid.uuid4().hex}.{EKSTENSI[fmt]}')


def cek_gambar(f, label='Gambar', wajib=True, **opsi):
    if not f:
        return None, ([f'{label} wajib diunggah (PNG/JPG/WEBP).'] if wajib else [])
    try:
        return bersihkan_gambar(f, label, **opsi), []
    except ValidationError as e:
        return None, list(e.messages)


def ganti_file(field, baru):
    lama = field.name if field else ''
    field.save(baru.name, baru, save=False)
    if lama and lama != field.name:
        field.storage.delete(lama)
