<script lang="ts">
  import Blockly from 'blockly/core';
  import En from 'blockly/msg/en';
  import 'blockly/blocks';
  import 'blockly/javascript';
  import BlocklyComponent, { type Locale } from 'blockly';

  // 1. Setup localization
  const en: Locale = {
    rtl: false,
    msg: {
      ...En,
    },
  };

  // 2. Define Blockly configuration & toolbox
  const config = {
    toolbox: `
      <xml xmlns="https://google.com">
        <block type="controls_if"></block>
        <block type="logic_compare"></block>
        <block type="math_number">
          <field name="NUM">123</field>
        </block>
        <block type="math_arithmetic"></block>
      </xml>
    `,
    scrollbars: true,
    trashcan: true,
  };

  // 3. Reference to the workspace instance
  let workspace: Blockly.WorkspaceSvg | undefined = $state();
  let generatedCode = $state('');

  function updateCode() {
    if (workspace) {
      // Example: Transpile blocks to JavaScript
      generatedCode = (Blockly as any).JavaScript.workspaceToCode(workspace);
    }
  }
</script>

<div class="container">
  <div class="blockly-wrapper">
    <BlocklyComponent
      {config}
      locale={en}
      bind:workspace
      onchange={updateCode}
    />
  </div>

  <div class="output">
    <h3>Generated Code:</h3>
    <pre>{generatedCode}</pre>
  </div>
</div>

<style>
  .container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    gap: 1rem;
    padding: 1rem;
  }
  .blockly-wrapper {
    flex: 1;
    min-height: 400px;
    border: 1px solid #ccc;
  }
  .output {
    background: #f4f4f4;
    padding: 1rem;
    border-radius: 4px;
  }
</style>
