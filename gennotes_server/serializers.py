from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Relation, Variant


class SafeTagUpdateMixin(object):
    def update(self, instance, validated_data):
        """
        Update which only accepts 'tags' edits and checks for protected tags.
        """
        if ['tags'] != validated_data.keys():
            raise serializers.ValidationError(detail={
                'detail': "Edits should include the 'tags' field, "
                'and only this field. Your request is attempting to edit '
                'the following fields: {}'.format(validated_data.keys())})
        tag_data = validated_data['tags']

        # For PUT, check that special tags are retained and unchanged.
        if not self.partial:
            for tag in instance.special_tags:
                if tag in instance.tags and tag not in tag_data:
                    raise serializers.ValidationError(detail={
                        'detail': 'PUT requests must retain all special tags. '
                        'Your request is missing the tag: {}'.format(tag)})
        # Check that special tags are unchanged.
        for tag in instance.special_tags:
            if (tag in instance.tags and tag in tag_data and
                    tag_data[tag] != instance.tags[tag]):
                raise serializers.ValidationError(detail={
                    'detail': 'Updates (PUT or PATCH) must not attempt '
                    'to change the values for special tags. Your request '
                    'attempts to change the value for tag '
                    "'{}' from '{}' to '{}'".format(
                        tag, instance.tags[tag], tag_data[tag])})
        if self.partial:
            instance.tags.update(tag_data)
        else:
            instance.tags = tag_data
        instance.save()
        return instance


class UserSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serialize a User object.
    """

    class Meta:
        model = get_user_model()
        fields = ('id', 'username')


class RelationSerializer(SafeTagUpdateMixin,
                         serializers.HyperlinkedModelSerializer):
    """
    Serialize a Relation object.

    API-mediated updates to Relations may only be performed for the tags field.

    POST create must include required tags (e.g. type).

    PUT update overwrites all tags with the tags data in the request. Any
    existing special tags data (e.g. type) must be retained and unchanged.

    PATCH update will update any tags included in the request tag data. If
    special tags are listed, their values must be unchanged.
    """
    class Meta:
        model = Relation

    def create(self, validated_data):
        """
        Check that all required tags are included in tag data before creating.
        """
        if 'tags' in validated_data:
            for tag in Relation.required_tags:
                if tag not in validated_data['tags']:
                    raise serializers.ValidationError(detail={
                        'detail': 'Create (POST) tag data must include all '
                        'required tags: {}'.format(Relation.required_tags)})
        return super(RelationSerializer, self).create(validated_data)


class VariantSerializer(SafeTagUpdateMixin,
                        serializers.HyperlinkedModelSerializer):
    """
    Serialize a Variant object.

    API-mediated updates to Variants may only be performed for the tags field.

    PUT update overwrites all tags with the tags data in the request. Any
    existing special tags data (e.g. build 37 position) must be retained and
    unchanged.

    PATCH update will update any tags included in the request tag data. If
    special tags are listed, their values must be unchanged.
    """
    b37_id = serializers.SerializerMethodField()
    relation_set = RelationSerializer(many=True, required=False)

    class Meta:
        model = Variant

    @staticmethod
    def get_b37_id(obj):
        """
        Return an ID like "b37-1-883516-G-A".
        """
        return '-'.join([
            'b37',
            obj.tags['chrom-b37'],
            obj.tags['pos-b37'],
            obj.tags['ref-allele-b37'],
            obj.tags['var-allele-b37'],
        ])
