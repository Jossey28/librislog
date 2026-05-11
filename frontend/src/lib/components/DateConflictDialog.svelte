<script lang="ts">
	import { _ } from '$lib/i18n';

	let {
		open = false,
		field = 'date_started',
		existingDate,
		suggestedDate,
		onKeep,
		onUseSuggested,
		onCancel
	}: {
		open?: boolean;
		field?: 'date_started' | 'date_finished';
		existingDate: string;
		suggestedDate: string;
		onKeep?: () => void;
		onUseSuggested?: () => void;
		onCancel?: () => void;
	} = $props();

	const typeKey = $derived(field === 'date_finished' ? 'finished' : 'started');
</script>

{#if open}
	<div class="modal modal-open">
		<div class="modal-box max-w-md">
			<h3 class="text-lg font-bold">{$_(`dateConflict.${typeKey}.title`)}</h3>
			<p class="text-sm text-base-content/70 mt-2">
				{$_(`dateConflict.${typeKey}.message`, {
					values: { oldDate: existingDate, newDate: suggestedDate }
				})}
			</p>
			<div class="modal-action">
				<button type="button" class="btn btn-ghost btn-sm" onclick={onCancel}>{$_('common.cancel')}</button>
				<button type="button" class="btn btn-outline btn-sm" onclick={onKeep}
					>{$_(`dateConflict.${typeKey}.keepOld`, { values: { oldDate: existingDate } })}</button
				>
				<button type="button" class="btn btn-primary btn-sm" onclick={onUseSuggested}
					>{$_(`dateConflict.${typeKey}.useNew`, { values: { newDate: suggestedDate } })}</button
				>
			</div>
		</div>
		<div class="modal-backdrop" role="button" tabindex="-1"></div>
	</div>
{/if}
