<script lang="ts">
	import { _ } from '$lib/i18n';

	let { value = $bindable(null), readonly = false, onChange }: {
		value?: number | null;
		readonly?: boolean;
		onChange?: (rating: number) => void;
	} = $props();
</script>

<div class="rating rating-sm">
	{#each [1, 2, 3, 4, 5] as star}
		<input
			type="radio"
			name="rating-{Math.random()}"
			class="mask mask-star-2 bg-warning"
			checked={value === star}
			disabled={readonly}
			onclick={() => !readonly && onChange?.(star)}
			aria-label={$_('common.starLabel', { values: { star } })}
		/>
	{/each}
</div>
