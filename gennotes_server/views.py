import datetime
import json

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404

from oauth2_provider.views import (ApplicationRegistration,
                                   ApplicationUpdate)
from oauth2_provider.ext.rest_framework import TokenHasScope

import rest_framework
from rest_framework import viewsets as rest_framework_viewsets
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from reversion import revisions as reversion

from .forms import EditingAppRegistrationForm
from .models import CommitDeletion, Relation, Variant, EditingApplication
from .permissions import EditAuthorizedOrReadOnly
from .serializers import RelationSerializer, UserSerializer, VariantSerializer


class VariantLookupMixin(object):
    """
    Mixin method for looking up a variant according to b37 position.
    """

    def _custom_variant_filter_kwargs(self, variant_lookup):
        """
        For a variant lookup string, return the variant filter arguments.
        """
        try:
            parts = variant_lookup.split('-')
            if parts[0] == 'b37':
                return {
                    'tags__chrom_b37': parts[1],
                    'tags__pos_b37': parts[2],
                    'tags__ref_allele_b37': parts[3],
                    'tags__var_allele_b37': parts[4],
                }
        except IndexError:
            return None
        return None


class RevisionUpdateMixin(object):
    """
    ViewSet mixin to record django-reversion revision, report current version.
    """
    @transaction.atomic()
    @reversion.create_revision()
    def update(self, request, *args, **kwargs):
        """
        Custom update method that records revisions and reports new version.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance,
                                         data=request.data,
                                         partial=partial,
                                         context={'request': request})
        serializer.is_valid(raise_exception=True)

        commit_comment = self.request.data.get('commit-comment', '')
        reversion.set_comment(comment=commit_comment)
        reversion.set_user(user=self.request.user)
        self.perform_update(serializer)

        return Response(serializer.data)


class VariantViewSet(VariantLookupMixin,
                     RevisionUpdateMixin,
                     rest_framework.mixins.RetrieveModelMixin,
                     rest_framework.mixins.ListModelMixin,
                     rest_framework.mixins.CreateModelMixin,
                     rest_framework.mixins.UpdateModelMixin,
                     rest_framework_viewsets.GenericViewSet):
    """
    A viewset for Variants, allowing id and position-based lookups.

    In addition to lookup by primary key, Variants may be referenced by
    build 37 information (e.g. 'b37-1-123456-C-T'). Bulk GET requests can be
    formed by specifying a list of variants as a parameter.

    Uses django-reversion to record the revision, user, and commit comment.

    See API Guide for more info.
    """
    permission_classes = (EditAuthorizedOrReadOnly,)
    required_scopes = ['commit-edit']
    queryset = Variant.objects.all()
    serializer_class = VariantSerializer

    def get_queryset(self, *args, **kwargs):
        """
        Return all variant data, or a subset if a specific list is requested.
        """
        queryset = super(VariantViewSet, self).get_queryset(*args, **kwargs)

        variant_list_json = self.request.query_params.get('variant_list', None)
        if not variant_list_json:
            return queryset
        variant_list = json.loads(variant_list_json)

        # Combine the variant list to make a single db query.
        Q_obj = None
        for variant_lookup in variant_list:
            if variant_lookup.isdigit():
                filter_kwargs = {'id': variant_lookup}
            else:
                filter_kwargs = self._custom_variant_filter_kwargs(variant_lookup)
            if filter_kwargs:
                if not Q_obj:
                    Q_obj = Q(**filter_kwargs)
                else:
                    Q_obj = Q_obj | Q(**filter_kwargs)
        queryset = queryset.filter(Q_obj)
        return queryset

    def get_object(self):
        """
        Primary key lookup if pk numeric, otherwise use custom filter kwargs.

        This allows us to also support build 37 lookup by chromosome, position,
        reference and variant.
        """
        if self.kwargs['pk'].isdigit():
            return super(VariantViewSet, self).get_object()

        queryset = self.filter_queryset(self.get_queryset())

        filter_kwargs = self._custom_variant_filter_kwargs(self.kwargs['pk'])
        if not filter_kwargs:
            raise Http404('No {} matches the given query.'.format(
                queryset.model._meta.object_name))

        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj

    @transaction.atomic()
    @reversion.create_revision()
    def create(self, request, *args, **kwargs):
        commit_comment = request.data.get('commit-comment', '')
        reversion.set_user(user=self.request.user)
        reversion.set_comment(comment=commit_comment)
        return super(VariantViewSet, self).create(request, *args, **kwargs)


# http GET localhost:8000/api/relation/   # all relations
# http GET localhost:8000/api/relation/2/ # relation with ID 2
# http -a youruser:yourpass PATCH localhost:8000/api/relation/2/ \
#  tags:='{"foo": "bar"}'                # set tags to '{"foo": "bar"}'
class RelationViewSet(RevisionUpdateMixin,
                      rest_framework.viewsets.ModelViewSet):
    """
    A viewset for Relations.

    Updating ('PUT', 'PATCH', 'POST', and "DELETE") uses django-reversion to record
    the revision, user, and commit comment. See API Guide for more info.
    """
    permission_classes = (EditAuthorizedOrReadOnly,)
    required_scopes = ['commit-edit']
    queryset = Relation.objects.all()
    serializer_class = RelationSerializer

    @transaction.atomic()
    @reversion.create_revision()
    def create(self, request, *args, **kwargs):
        commit_comment = request.data.get('commit-comment', '')
        reversion.set_user(user=self.request.user)
        reversion.set_comment(comment=commit_comment)
        return super(RelationViewSet, self).create(request, *args, **kwargs)

    @transaction.atomic()
    @reversion.create_revision()
    def record_destroy(self, request, instance):
        commit_comment = request.data.get('commit-comment', '')
        instance.save()
        reversion.set_user(user=self.request.user)
        reversion.set_comment(comment=commit_comment)
        reversion.add_meta(CommitDeletion)

    def destroy(self, request, *args, **kwargs):
        """
        Check version is the latest. If so: record CommitDeletion, then delete.
        """
        if 'edited_version' not in request.data:
            raise rest_framework.serializers.ValidationError(detail={
                'detail':
                    'Delete sumbissions to the API must include a parameter '
                    "'edited_version' that reports the version ID of the item "
                    'being deleted.'
            })
        instance = self.get_object()
        current_version = reversion.get_for_date(
            instance, datetime.datetime.now()).id
        if not current_version == request.data['edited_version']:
            raise rest_framework.serializers.ValidationError(detail={
                'detail':
                    'Edit conflict error! The current version for this object '
                    'does not match the reported version being deleted.',
                'current_version': current_version,
                'submitted_data': self.context['request'].data,
            })
        self.record_destroy(request, instance)
        return super(RelationViewSet, self).destroy(request, *args, **kwargs)


class CurrentUserView(RetrieveAPIView):
    """
    A viewset that returns the current user id, username, and email.
    """
    permission_classes = (TokenHasScope,)
    required_scopes = ['username', 'email']

    model = get_user_model()
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class EditingAppRegistration(ApplicationRegistration):
    form_class = EditingAppRegistrationForm

    def form_valid(self, form):
        form.instance.client_type = EditingApplication.CLIENT_CONFIDENTIAL
        form.instance.authorization_grant_type = EditingApplication.GRANT_AUTHORIZATION_CODE
        return super(EditingAppRegistration, self).form_valid(form)


class EditingAppUpdate(ApplicationUpdate):
    fields = ['name', 'description', 'redirect_uris']
