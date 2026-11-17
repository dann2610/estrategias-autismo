"""Pruebas de la plataforma «Estrategias de apoyo en el autismo».

Ejecutar:  python manage.py test
"""
import re
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.comments.models import Comment
from apps.core.choices import Status
from apps.core.models import SiteConfig
from apps.directory.models import Institution
from apps.exchange.models import ExchangeItem
from apps.interviews.models import Interview
from apps.learn.models import Capsule
from apps.moderation.models import ModerationAction
from apps.moderation.services import transition
from apps.practice.models import Activity, Material, Pictogram

A = ModerationAction.Action
MEDIA = tempfile.mkdtemp()
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@override_settings(MEDIA_ROOT=MEDIA, ALLOWED_HOSTS=["*"])
class PlataformaTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("cargar_contenido", verbosity=0)
        U = get_user_model()
        cls.familia = U.objects.create_user(email="familia@ejemplo.org", password="Clave-segura-2026")
        cls.otra = U.objects.create_user(email="otra@ejemplo.org", password="Clave-segura-2026")
        cls.mod = U.objects.create_user(email="mod@ejemplo.org", password="Clave-segura-2026", is_staff=True)
        cls.mod.groups.add(Group.objects.get(name="Moderadores"))

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()

    def login(self, user):
        self.client.force_login(user)

    def new_exchange(self, user, **extra):
        data = dict(title="Cuentos con pictogramas", offer="ofrezco", item_kind="libro", condition="bueno",
                    description="Tres cuentos en buen estado.", province="Guayas", canton="Milagro",
                    contact_authorized="Correo de contacto en el perfil", delivery_terms="Préstamo por un mes",
                    safety_confirmed="on", accept_rules="on")
        data.update(extra)
        self.login(user)
        r = self.client.post(reverse("contributions:create", args=["intercambio"]), data)
        self.assertEqual(r.status_code, 302, getattr(r, "context", {}) and r.context["form"].errors)
        return ExchangeItem.objects.latest("pk")

    # 1. Contenido inicial
    def test_carga_idempotente_y_sin_contenido_inventado(self):
        call_command("cargar_contenido", verbosity=0)
        self.assertEqual(Capsule.objects.count(), 9)
        self.assertEqual(Activity.objects.count(), 9)
        self.assertEqual(Material.objects.count(), 10)
        self.assertEqual(Institution.objects.count(), 5)
        self.assertEqual(Pictogram.objects.count(), 54)
        self.assertEqual(ExchangeItem.objects.count(), 0)
        self.assertEqual(Comment.objects.count(), 0)
        iv = Interview.objects.get()
        self.assertFalse(iv.is_public)
        self.assertFalse(iv.authorization_confirmed)

    # 2. Cada cápsula conecta con recursos prácticos y fuentes
    def test_capsulas_completas_y_conectadas(self):
        for c in Capsule.objects.public():
            self.assertTrue(c.sources.exists(), c)
            self.assertTrue(c.has_practical_resource(), c)
            self.assertEqual(c.publication_problems(), [], c)
            html = self.client.get(c.get_absolute_url()).content.decode()
            self.assertIn("De la explicación a la práctica", html, c)
            self.assertIn("Fuentes", html, c)

    # 3. Actividades con todos los campos obligatorios
    def test_actividades_tienen_estructura_completa(self):
        for a in Activity.objects.public():
            for f in ("objective", "materials_needed", "instructions", "adaptations", "precautions", "age_range"):
                self.assertTrue(getattr(a, f), f"{a}: falta {f}")
            r = self.client.get(a.get_absolute_url())
            self.assertContains(r, "no reemplaza", msg_prefix=str(a))

    # 4. Páginas públicas, impresión y agenda
    def test_paginas_publicas(self):
        for name in ("core:home", "core:orientation", "core:sources", "learn:index", "learn:faq", "practice:hub",
                     "practice:activities", "practice:materials", "practice:pictograms", "practice:agenda",
                     "practice:videos", "directory:index", "interviews:index", "exchange:index", "exchange:rules",
                     "core:rules", "core:credits", "core:privacy"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for m in Material.objects.public():
            r = self.client.get(reverse("practice:material_print", args=[m.pk]))
            self.assertEqual(r.status_code, 200, m)
        r = self.client.get(reverse("practice:agenda"))
        self.assertContains(r, 'id="pictos" type="application/json"')
        self.assertNotContains(r, "<script>")

    def test_filtros_y_busqueda(self):
        r = self.client.get(reverse("practice:activities"), {"lugar": "escuela"})
        self.assertContains(r, "Anticipar la jornada en el aula")
        r = self.client.get(reverse("core:search"), {"q": "agenda"})
        self.assertContains(r, "Agenda visual de la mañana")

    # 5. Entrevista sin contenido inventado
    def test_entrevista_proximamente_y_aprobacion_bloqueada(self):
        iv = Interview.objects.get()
        r = self.client.get(reverse("interviews:index"))
        self.assertContains(r, "próximamente", status_code=200)
        self.assertEqual(self.client.get(reverse("interviews:detail", args=[iv.pk])).status_code, 200)
        iv.status = Status.PENDING
        iv.save()
        with self.assertRaises(ValidationError) as ctx:
            transition(iv, self.mod, A.APPROVE)
        self.assertIn("autoriz", " ".join(ctx.exception.messages).lower())

    # 6. Cápsula sin recursos o sin fuentes no se publica
    def test_capsula_sin_recurso_no_se_aprueba(self):
        c = Capsule.objects.create(title="Prueba", theme="mitos", description="x", explanation="x",
                                   revised_on="2026-10-28", status=Status.PENDING)
        with self.assertRaises(ValidationError):
            transition(c, self.mod, A.APPROVE)

    # 7. Institución sugerida por la comunidad: pendiente de verificación y no publicable sin respaldo
    def test_institucion_sugerida_requiere_verificacion(self):
        self.login(self.familia)
        r = self.client.post(reverse("contributions:create", args=["institucion"]), {
            "title": "Centro de prueba", "kind": "terapeutico", "description": "Lo vi en redes.",
            "services": "Terapias", "province": "Guayas", "canton": "Milagro", "accept_rules": "on"})
        self.assertEqual(r.status_code, 302)
        inst = Institution.objects.get(title="Centro de prueba")
        self.assertEqual(inst.verification_basis, "pendiente")
        transition(inst, self.familia, A.SUBMIT)
        with self.assertRaises(ValidationError):
            transition(inst, self.mod, A.APPROVE)
        self.assertNotContains(self.client.get(reverse("directory:index")), "Centro de prueba")

    def test_directorio_muestra_base_de_verificacion(self):
        r = self.client.get(reverse("directory:index"))
        self.assertContains(r, "APADA del Ecuador")
        inst = Institution.objects.get(title__startswith="Calificación")
        r = self.client.get(inst.get_absolute_url())
        self.assertContains(r, "gob.ec")
        self.assertContains(r, "Información pública")

    # 8. Flujo de moderación del intercambio
    def test_intercambio_moderado(self):
        item = self.new_exchange(self.familia)
        self.assertEqual(item.status, Status.DRAFT)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("exchange:detail", args=[item.pk])).status_code, 404)
        transition(item, self.familia, A.SUBMIT)
        self.assertEqual(self.client.get(reverse("exchange:detail", args=[item.pk])).status_code, 404)
        transition(item, self.mod, A.APPROVE)
        r = self.client.get(reverse("exchange:detail", args=[item.pk]))
        self.assertContains(r, "Cuentos con pictogramas")

    # 9. Contacto oculto para visitantes
    def test_contacto_solo_para_usuarios_registrados(self):
        item = self.new_exchange(self.familia)
        transition(item, self.familia, A.SUBMIT)
        transition(item, self.mod, A.APPROVE)
        self.client.logout()
        r = self.client.get(item.get_absolute_url())
        self.assertNotContains(r, "Correo de contacto en el perfil")
        self.assertContains(r, "Ingresa para ver el contacto")
        self.login(self.otra)
        self.assertContains(self.client.get(item.get_absolute_url()), "Correo de contacto en el perfil")

    # 10. Disponibilidad: solo el autor
    def test_disponibilidad_solo_autor(self):
        item = self.new_exchange(self.familia)
        transition(item, self.familia, A.SUBMIT)
        transition(item, self.mod, A.APPROVE)
        url = reverse("exchange:availability", args=[item.pk])
        self.login(self.otra)
        self.assertIn(self.client.post(url, {"availability": "finalizado"}).status_code, (403, 404))
        item.refresh_from_db()
        self.assertEqual(item.availability, "disponible")
        self.login(self.familia)
        self.client.post(url, {"availability": "finalizado"})
        item.refresh_from_db()
        self.assertEqual(item.availability, "finalizado")
        self.assertNotContains(self.client.get(reverse("exchange:index")), "Cuentos con pictogramas")

    def test_intercambio_desactivable(self):
        cfg = SiteConfig.load()
        cfg.allow_exchange = False
        cfg.save()
        self.assertEqual(self.client.get(reverse("exchange:index")).status_code, 404)

    # 11. Comentarios moderados, anti-spam y datos sensibles
    def test_comentarios(self):
        cap = Capsule.objects.public().first()
        url = reverse("comments:add", args=[cap.pk])
        self.assertEqual(self.client.post(url, {"description": "Hola"}).status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)  # visitante: debe ingresar
        self.login(self.familia)
        self.client.post(url, {"description": "Gracias", "website": "http://spam.example"})
        self.assertEqual(Comment.objects.count(), 0)  # honeypot
        self.client.post(url, {"description": "Mi número es 0991234567"})
        self.assertEqual(Comment.objects.count(), 0)  # dato sensible
        self.client.post(url, {"description": "Muy útil la agenda, gracias."})
        c = Comment.objects.get()
        self.assertEqual(c.status, Status.PENDING)
        self.client.logout()
        self.assertNotContains(self.client.get(cap.get_absolute_url()), "Muy útil la agenda")
        transition(c, self.mod, A.APPROVE)
        self.assertContains(self.client.get(cap.get_absolute_url()), "Muy útil la agenda")

    # 12. Permisos del panel
    def test_panel_solo_moderacion(self):
        self.assertNotEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
        self.login(self.familia)
        self.assertIn(self.client.get(reverse("dashboard:home")).status_code, (302, 403))
        self.login(self.mod)
        for name in ("dashboard:home", "dashboard:inbox", "dashboard:quality"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_usuario_no_aprueba_su_aporte(self):
        item = self.new_exchange(self.familia)
        transition(item, self.familia, A.SUBMIT)
        with self.assertRaises(Exception):
            transition(item, self.familia, A.APPROVE)
        self.login(self.otra)
        r = self.client.get(reverse("contributions:summary", args=[item.model_key, item.pk]))
        self.assertIn(r.status_code, (403, 404))

    # 13. Archivos: validación y acceso privado
    def test_archivo_falso_rechazado(self):
        self.login(self.familia)
        fake = SimpleUploadedFile("agenda.pdf", b"MZ\x90\x00 no es un pdf", content_type="application/pdf")
        r = self.client.post(reverse("contributions:create", args=["material"]), {
            "title": "Mi agenda", "kind": "agenda", "description": "Agenda", "how_to_use": "Imprimir",
            "file": fake, "age_range": "todas", "audience": "familias", "credit": "Yo", "license": "Libre",
            "rights_confirmed": "on", "accept_rules": "on"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Material.objects.filter(title="Mi agenda").count(), 0)

    def test_archivos_privados_protegidos(self):
        inst = Institution.objects.first()
        inst.evidence_document = SimpleUploadedFile("respaldo.pdf", PDF)
        inst.save()
        url = reverse("core:file", args=[inst.model_key, inst.pk, "evidence_document"])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.login(self.familia)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.login(self.mod)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_archivo_de_material_no_aprobado_oculto(self):
        self.login(self.familia)
        r = self.client.post(reverse("contributions:create", args=["material"]), {
            "title": "Mi agenda", "kind": "agenda", "description": "Agenda de la tarde", "how_to_use": "Imprimir",
            "file": SimpleUploadedFile("agenda.pdf", PDF, content_type="application/pdf"), "age_range": "todas",
            "audience": "familias", "credit": "Equipo familiar", "license": "Uso libre con atribución",
            "rights_confirmed": "on", "accept_rules": "on"})
        self.assertEqual(r.status_code, 302)
        m = Material.objects.get(title="Mi agenda")
        url = reverse("core:file", args=[m.model_key, m.pk, "file"])
        self.assertEqual(self.client.get(url).status_code, 200)  # su autora sí
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 404)

    # 14. API pública solo devuelve contenido aprobado
    def test_api(self):
        r = self.client.get("/api/pictogramas/")
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/api/actividades/")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("borrador", r.content.decode())

    # 15. Seguridad básica
    def test_cabeceras_de_seguridad(self):
        r = self.client.get("/")
        self.assertIn("default-src 'self'", r.get("Content-Security-Policy", ""))
        self.assertNotIn("<script>", r.content.decode())

    # 16. Sin enlaces internos rotos (visitante, usuario y moderación)
    def test_sin_enlaces_rotos(self):
        for user in (None, self.familia, self.mod):
            self.client.logout()
            if user:
                self.login(user)
            seen, todo, bad = set(), ["/"], []
            while todo and len(seen) < 400:
                u = todo.pop()
                if u in seen:
                    continue
                seen.add(u)
                r = self.client.get(u)
                if r.status_code >= 400:
                    bad.append((u, r.status_code))
                elif r.status_code == 200 and "html" in r.get("Content-Type", ""):
                    for h in re.findall(r'href="(/[^"#]*)"', r.content.decode()):
                        h = h.replace("&amp;", "&")
                        if not h.startswith(("/static", "/media", "/gestion-django", "/cuenta/salir")):
                            todo.append(h)
            self.assertEqual(bad, [], f"Usuario {user}")
            self.assertGreater(len(seen), 100)
