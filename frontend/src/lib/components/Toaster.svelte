<script lang="ts">
	import { toasts, type ToastLevel } from '$lib/toasts';

	const CLASSES: Record<ToastLevel, string> = {
		error: 'alert-error',
		warning: 'alert-warning',
		success: 'alert-success',
		info: 'alert-info'
	};
</script>

<div class="toast toast-top toast-end z-[100] pointer-events-none">
	{#each $toasts as toast (toast.id)}
		<div class="alert {CLASSES[toast.level]} shadow-lg pointer-events-auto max-w-sm">
			<span class="text-sm">{toast.message}</span>
			<button
				class="btn btn-ghost btn-xs ml-auto"
				onclick={() => toasts.remove(toast.id)}
				aria-label="Dismiss"
			>✕</button>
		</div>
	{/each}
</div>
