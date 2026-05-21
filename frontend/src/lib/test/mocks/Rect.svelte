<script>
	let { role, ...rest } = $props();
</script>

<div {role} data-testid="rect" {...rest}></div>
