"""
Django admin registration for CourseShare Hub.  Owner: Tianyang (data backbone).

A configured admin gives every model owner a fast way to create/inspect data
during testing, and reads as polish during the demo. See docs/PROJECT_PLAN.md §5.2.
"""
from django.contrib import admin

from .models import (
    Category, Course, Tag, Resource, SavedSearch, UserProfile,
    ContactMessage, UserHistory, DailyVisitLog, Comment, Favourite,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'term', 'created_at')
    list_filter = ('term',)
    search_fields = ('code', 'title')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'category', 'file_type', 'uploader', 'is_public', 'created_at')
    list_filter = ('file_type', 'is_public', 'category', 'course')
    search_fields = ('title', 'description')
    autocomplete_fields = ('course', 'category', 'uploader')
    filter_horizontal = ('tags',)
    readonly_fields = ('views_count', 'download_count', 'created_at', 'updated_at')


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ('user', 'keyword', 'course', 'category', 'file_type', 'created_at')
    search_fields = ('keyword',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'program')
    search_fields = ('user__username', 'student_id')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('subject', 'name', 'email')


@admin.register(UserHistory)
class UserHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'resource', 'keyword', 'created_at')
    list_filter = ('action',)
    search_fields = ('user__username', 'keyword')


@admin.register(DailyVisitLog)
class DailyVisitLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key', 'date', 'visit_count')
    list_filter = ('date',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('resource', 'author', 'created_at')
    search_fields = ('body',)


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource', 'created_at')
