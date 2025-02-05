import structlog

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormMixin

from versions.models import Version
from .forms import LibraryForm, VersionSelectionForm
from .models import Category, Issue, Library, LibraryVersion, PullRequest

logger = structlog.get_logger()


class CategoryMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all().order_by("name")
        return context


class LibraryList(CategoryMixin, FormMixin, ListView):
    """List all of our libraries for the current version of Boost by name"""

    form_action = "/libraries/"
    form_class = LibraryForm
    queryset = (
        Library.objects.prefetch_related("authors", "categories").all().order_by("name")
    )
    template_name = "libraries/list.html"

    def get_context_data(self, **kwargs):
        """Set the form action to the main libraries page"""
        context = super().get_context_data(**kwargs)
        context["form_action"] = self.form_action
        return context

    def get_queryset(self):
        version = Version.objects.most_recent()
        return (
            super().get_queryset().filter(library_version__version=version).distinct()
        )

    def post(self, request):
        """User has submitted a form and will be redirected to the right results"""
        form = self.get_form()
        if form.is_valid():
            category = form.cleaned_data["categories"][0]
            return redirect("libraries-by-category", category=category.slug)
        else:
            logger.info("library_list_invalid_category")
        return super().get(request)


class LibraryDetail(CategoryMixin, FormMixin, DetailView):
    """Display a single Library in insolation"""

    form_class = VersionSelectionForm
    model = Library
    template_name = "libraries/detail.html"

    def get_context_data(self, **kwargs):
        """Set the form action to the main libraries page"""
        context = super().get_context_data(**kwargs)
        context["closed_prs_count"] = self.get_closed_prs_count(self.object)
        context["open_issues_count"] = self.get_open_issues_count(self.object)
        context["version"] = self.get_version()
        context["maintainers"] = self.get_maintainers(context["version"])
        context["versions"] = (
            Version.objects.active()
            .filter(library_version__library=self.object)
            .distinct()
            .order_by("-release_date")
        )
        return context

    def get_object(self):
        """Get the current library object from the slug in the URL.
        If present, use the version_slug to get the right LibraryVersion of the library.
        Otherwise, default to the most recent version."""
        slug = self.kwargs.get("slug")
        version = self.get_version()

        if not LibraryVersion.objects.filter(
            version=version, library__slug=slug
        ).exists():
            raise Http404("No library found matching the query")

        try:
            obj = self.get_queryset().get(slug=slug)
        except self.model.DoesNotExist:
            raise Http404("No library found matching the query")
        return obj

    def get_closed_prs_count(self, obj):
        """Get the number of closed pull requests for the current library."""
        return PullRequest.objects.filter(library=obj, is_open=True).count()

    def get_maintainers(self, version):
        """Get the maintainers for the current LibraryVersion."""
        obj = self.get_object()
        library_version = LibraryVersion.objects.get(library=obj, version=version)
        return library_version.maintainers.all()

    def get_open_issues_count(self, obj):
        """Get the number of open issues for the current library."""
        return Issue.objects.filter(library=obj, is_open=True).count()

    def get_version(self):
        """Get the version of Boost for the library we're currently looking at."""
        version_slug = self.kwargs.get("version_slug")
        if version_slug:
            return get_object_or_404(Version, slug=version_slug)
        else:
            return Version.objects.most_recent()

    def post(self, request, *args, **kwargs):
        """User has submitted a form and will be redirected to the right LibraryVersion."""
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            version = form.cleaned_data["version"]
            return redirect(
                "library-detail-by-version",
                version_slug=version.slug,
                slug=self.object.slug,
            )
        else:
            logger.info("library_list_invalid_version")
        return super().get(request)


class LibraryByCategory(CategoryMixin, FormMixin, ListView):
    """List all of our libraries for the current version of Boost in a certain category"""

    form_action = "/libraries/"
    form_class = LibraryForm
    paginate_by = 25
    template_name = "libraries/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        category_slug = self.kwargs.get("category")
        context["version"] = Version.objects.most_recent()
        context["form_action"] = self.form_action

        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug)
                context["category"] = category
            except Category.DoesNotExist:
                logger.info("libraries_by_category_view_category_not_found")
        return context

    def get_queryset(self):
        category = self.kwargs.get("category")
        version = Version.objects.most_recent()

        return (
            Library.objects.prefetch_related("categories")
            .filter(
                categories__slug=category,
                versions__library_version__version=version,
            )
            .order_by("name")
            .distinct()
        )


class LibraryListByVersion(CategoryMixin, FormMixin, ListView):
    """List all of our libraries for a specific Boost version by name"""

    form_class = LibraryForm
    queryset = (
        Library.objects.prefetch_related("authors", "categories").all().order_by("name")
    )
    template_name = "libraries/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            version = Version.objects.get(slug=self.kwargs.get("slug"))
            context["version_slug"] = self.kwargs.get("slug")
            context["version_name"] = version.name
            context["version"] = version
        except Version.DoesNotExist:
            raise Http404("No library found matching the query")

        context["form_action"] = f"/versions/{self.kwargs.get('slug')}/libraries/"
        return context

    def get_queryset(self):
        version_slug = self.kwargs.get("slug")
        return (
            super().get_queryset().filter(library_version__version__slug=version_slug)
        )

    def post(self, request, *args, **kwargs):
        """User has submitted a form and will be redirected to the right results"""
        form = self.get_form()
        if form.is_valid():
            category = form.cleaned_data["categories"][0]
            return redirect(
                "libraries-by-version-by-category",
                version_slug=self.kwargs.get("slug"),
                category=category.slug,
            )
        else:
            logger.info("library_list_invalid_category")
        return super().get(request)


class LibraryListByVersionByCategory(CategoryMixin, FormMixin, ListView):
    """List all of our libraries in a certain category for a certain Boost version"""

    form_class = LibraryForm
    paginate_by = 25
    queryset = (
        Library.objects.prefetch_related("authors", "categories").all().order_by("name")
    )
    template_name = "libraries/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        category_slug = self.kwargs.get("category")
        version_slug = self.kwargs.get("version_slug")
        context[
            "form_action"
        ] = f"/versions/{self.kwargs.get('version_slug')}/libraries/"

        try:
            version = Version.objects.get(slug=version_slug)
            context["version_slug"] = version_slug
            context["version_name"] = version.name
            context["version"] = version
        except Version.DoesNotExist:
            raise Http404("No library found matching the query")

        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug)
                context["category"] = category
            except Category.DoesNotExist:
                logger.info("libraries_by_category_view_category_not_found")
        return context

    def get_queryset(self, **kwargs):
        category = self.kwargs.get("category")
        version_slug = self.kwargs.get("version_slug")
        return (
            super()
            .get_queryset()
            .filter(
                categories__slug=category,
                versions__library_version__version__slug=version_slug,
            )
            .distinct()
        )

    def post(self, request, *args, **kwargs):
        """User has submitted a form and will be redirected to the right results"""
        form = self.get_form()
        if form.is_valid():
            category = form.cleaned_data["categories"][0]
            return redirect(
                "libraries-by-version-by-category",
                version_slug=self.kwargs.get("version_slug"),
                category=category.slug,
            )
        else:
            logger.info("library_list_invalid_category")
        return super().get(request)
