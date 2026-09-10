// Generated from FastAPI. Run pnpm generate:strategy-api; do not edit by hand.
export interface paths {
  '/api/v1/accounts': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Accounts */
    get: operations['accounts_api_v1_accounts_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/accounts/{account_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Account */
    get: operations['account_api_v1_accounts__account_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/accounts/{account_id}/balances/latest': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Latest Balance */
    get: operations['latest_balance_api_v1_accounts__account_id__balances_latest_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/accounts/{account_id}/equity-history': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Equity History */
    get: operations['equity_history_api_v1_accounts__account_id__equity_history_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/accounts/{account_id}/pnl/{instrument_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Pnl */
    get: operations['get_pnl_api_v1_accounts__account_id__pnl__instrument_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/accounts/{account_id}/positions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Account Positions */
    get: operations['account_positions_api_v1_accounts__account_id__positions_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/accounts/{account_id}/positions/{instrument_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Position */
    get: operations['get_position_api_v1_accounts__account_id__positions__instrument_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/instruments': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Instruments */
    get: operations['instruments_api_v1_instruments_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/instruments/{instrument_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Instrument */
    get: operations['instrument_api_v1_instruments__instrument_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/live-trading/sessions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Live Sessions */
    get: operations['get_live_sessions_api_v1_live_trading_sessions_get'];
    put?: never;
    /** Create Live Session */
    post: operations['create_live_session_api_v1_live_trading_sessions_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/live-trading/sessions/{session_id}/approve': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Approve Session */
    post: operations['approve_session_api_v1_live_trading_sessions__session_id__approve_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/live-trading/sessions/{session_id}/revoke': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Revoke Session */
    post: operations['revoke_session_api_v1_live_trading_sessions__session_id__revoke_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/ops/reconciliation-summary': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Reconciliation Summary */
    get: operations['reconciliation_summary_api_v1_ops_reconciliation_summary_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/security/credential-references': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Credential References */
    get: operations['credential_references_api_v1_security_credential_references_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/security/credential-rotations': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Credential Rotations */
    get: operations['credential_rotations_api_v1_security_credential_rotations_get'];
    put?: never;
    /** Create Credential Rotation */
    post: operations['create_credential_rotation_api_v1_security_credential_rotations_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/security/exchange-connectivity': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Exchange Connectivity */
    get: operations['exchange_connectivity_api_v1_security_exchange_connectivity_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/security/exchange-venue-readiness': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Exchange Venue Readiness */
    get: operations['exchange_venue_readiness_api_v1_security_exchange_venue_readiness_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/security/trading-safety': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Trading Safety */
    get: operations['trading_safety_api_v1_security_trading_safety_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/definitions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategies Definitions */
    get: operations['strategies_definitions_api_v1_strategies_definitions_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategies Instances */
    get: operations['strategies_instances_api_v1_strategies_instances_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategy Instance */
    get: operations['strategy_instance_api_v1_strategies_instances__strategy_instance_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/account-snapshot': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategy Account Snapshot */
    get: operations['strategy_account_snapshot_api_v1_strategies_instances__strategy_instance_id__account_snapshot_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/accounts': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategy Accounts */
    get: operations['strategy_accounts_api_v1_strategies_instances__strategy_instance_id__accounts_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/execution-risk-policy': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Read Execution Risk Policy */
    get: operations['read_execution_risk_policy_api_v1_strategies_instances__strategy_instance_id__execution_risk_policy_get'];
    /** Change Execution Risk Policy */
    put: operations['change_execution_risk_policy_api_v1_strategies_instances__strategy_instance_id__execution_risk_policy_put'];
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/financials/rebuild': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Rebuild Financials */
    post: operations['rebuild_financials_api_v1_strategies_instances__strategy_instance_id__financials_rebuild_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/formal-nav-snapshots': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Formal Nav Snapshots */
    get: operations['get_formal_nav_snapshots_api_v1_strategies_instances__strategy_instance_id__formal_nav_snapshots_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/formal-nav-snapshots/run': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Run Formal Nav */
    post: operations['run_formal_nav_api_v1_strategies_instances__strategy_instance_id__formal_nav_snapshots_run_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/formal-pnl': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Formal Pnl */
    get: operations['get_formal_pnl_api_v1_strategies_instances__strategy_instance_id__formal_pnl_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/formal-positions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Formal Positions */
    get: operations['get_formal_positions_api_v1_strategies_instances__strategy_instance_id__formal_positions_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/nav-snapshots': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategy Nav Snapshots */
    get: operations['strategy_nav_snapshots_api_v1_strategies_instances__strategy_instance_id__nav_snapshots_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/nav-snapshots/run': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Run Strategy Nav Snapshot */
    post: operations['run_strategy_nav_snapshot_api_v1_strategies_instances__strategy_instance_id__nav_snapshots_run_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/pnl': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategy Pnl */
    get: operations['strategy_pnl_api_v1_strategies_instances__strategy_instance_id__pnl_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/runs': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategy Runs */
    get: operations['strategy_runs_api_v1_strategies_instances__strategy_instance_id__runs_get'];
    put?: never;
    /** Create Run */
    post: operations['create_run_api_v1_strategies_instances__strategy_instance_id__runs_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/instances/{strategy_instance_id}/v1-readiness': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategy V1 Readiness */
    get: operations['strategy_v1_readiness_api_v1_strategies_instances__strategy_instance_id__v1_readiness_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/management-overview': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategy Management Overview */
    get: operations['strategy_management_overview_api_v1_strategies_management_overview_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/strategies/{strategy_instance_id}/instructions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Strategy Instructions */
    get: operations['strategy_instructions_api_v1_strategies__strategy_instance_id__instructions_get'];
    put?: never;
    /** Create Strategy Instruction */
    post: operations['create_strategy_instruction_api_v1_strategies__strategy_instance_id__instructions_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/system/runtime-readiness': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Runtime Readiness */
    get: operations['runtime_readiness_api_v1_system_runtime_readiness_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/commands': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Create Command */
    post: operations['create_command_api_v1_trading_commands_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/commands/{trade_command_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Trade Command */
    get: operations['trade_command_api_v1_trading_commands__trade_command_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/exit-plans': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Exit Plans */
    get: operations['exit_plans_api_v1_trading_cross_spread_exit_plans_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/exit-plans/evaluate': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Evaluate Market Exit Plans */
    post: operations['evaluate_market_exit_plans_api_v1_trading_cross_spread_exit_plans_evaluate_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/exit-plans/{plan_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    /** Update Exit Plan */
    patch: operations['update_exit_plan_api_v1_trading_cross_spread_exit_plans__plan_id__patch'];
    trace?: never;
  };
  '/api/v1/trading/cross-spread/exit-plans/{plan_id}/close': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Close Market Lifecycle */
    post: operations['close_market_lifecycle_api_v1_trading_cross_spread_exit_plans__plan_id__close_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/funding-transfer': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cross Spread Funding Transfer */
    post: operations['cross_spread_funding_transfer_api_v1_trading_cross_spread_funding_transfer_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/funding-transfer/quote': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Cross Spread Funding Transfer Quote */
    get: operations['cross_spread_funding_transfer_quote_api_v1_trading_cross_spread_funding_transfer_quote_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/funding-transfers/{transfer_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Cross Spread Funding Transfer Status */
    get: operations['cross_spread_funding_transfer_status_api_v1_trading_cross_spread_funding_transfers__transfer_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/funding-transfers/{transfer_id}/cancel': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cross Spread Funding Transfer Cancel */
    post: operations['cross_spread_funding_transfer_cancel_api_v1_trading_cross_spread_funding_transfers__transfer_id__cancel_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/history': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Cross Spread History */
    get: operations['cross_spread_history_api_v1_trading_cross_spread_history_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/leverage': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Cross Spread Leverage */
    get: operations['cross_spread_leverage_api_v1_trading_cross_spread_leverage_get'];
    put?: never;
    /** Set Cross Spread Leverage */
    post: operations['set_cross_spread_leverage_api_v1_trading_cross_spread_leverage_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/lifecycle/open': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Open Market Lifecycle */
    post: operations['open_market_lifecycle_api_v1_trading_cross_spread_lifecycle_open_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/market-command': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cross Spread Market Command */
    post: operations['cross_spread_market_command_api_v1_trading_cross_spread_market_command_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/observability': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Cross Spread Observability */
    get: operations['cross_spread_observability_api_v1_trading_cross_spread_observability_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/preflight': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cross Spread Preflight */
    post: operations['cross_spread_preflight_api_v1_trading_cross_spread_preflight_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/cross-spread/snapshot': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Cross Spread Snapshot */
    get: operations['cross_spread_snapshot_api_v1_trading_cross_spread_snapshot_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/execution-batches': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Execution Batches */
    get: operations['execution_batches_api_v1_trading_execution_batches_get'];
    put?: never;
    /** Create Batch */
    post: operations['create_batch_api_v1_trading_execution_batches_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/execution-batches/{batch_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Get Batch */
    get: operations['get_batch_api_v1_trading_execution_batches__batch_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/execution-batches/{batch_id}/risk': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Read Batch Risk */
    get: operations['read_batch_risk_api_v1_trading_execution_batches__batch_id__risk_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/execution-batches/{batch_id}/risk-actions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Read Risk Actions */
    get: operations['read_risk_actions_api_v1_trading_execution_batches__batch_id__risk_actions_get'];
    put?: never;
    /** Create Risk Action */
    post: operations['create_risk_action_api_v1_trading_execution_batches__batch_id__risk_actions_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/fills': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Fills */
    get: operations['fills_api_v1_trading_fills_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/funding/execution-context': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Funding Execution Context */
    get: operations['funding_execution_context_api_v1_trading_funding_execution_context_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/funding/instructions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Funding Instruction By Idempotency */
    get: operations['funding_instruction_by_idempotency_api_v1_trading_funding_instructions_get'];
    put?: never;
    /** Funding Instruction Submit */
    post: operations['funding_instruction_submit_api_v1_trading_funding_instructions_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/funding/instructions/{instruction_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Funding Instruction Workspace */
    get: operations['funding_instruction_workspace_api_v1_trading_funding_instructions__instruction_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/funding/market-command': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Funding Market Command */
    post: operations['funding_market_command_api_v1_trading_funding_market_command_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/funding/positions': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Funding Positions */
    get: operations['funding_positions_api_v1_trading_funding_positions_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/orders': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Orders */
    get: operations['orders_api_v1_trading_orders_get'];
    put?: never;
    /**
     * Compatibility order endpoint; use TradeCommand or ExecutionBatch
     * @deprecated
     */
    post: operations['create_order_api_v1_trading_orders_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/orders/{order_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Order */
    get: operations['order_api_v1_trading_orders__order_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/orders/{order_id}/reconcile': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Recover an uncertain order from Runtime Journal */
    post: operations['reconcile_trading_order_api_v1_trading_orders__order_id__reconcile_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/orders/{order_id}/resolve-missing-external': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Resolve Missing External Platform Order */
    post: operations['resolve_missing_external_platform_order_api_v1_trading_orders__order_id__resolve_missing_external_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/trading/orders/{order_id}/venue-reconcile': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Reconcile Platform Order */
    post: operations['reconcile_platform_order_api_v1_trading_orders__order_id__venue_reconcile_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    /** AccountResponse */
    AccountResponse: {
      /** Accountcode */
      accountCode: string;
      /** Accountid */
      accountId: string;
      /** Accounttype */
      accountType: string;
      /** Basecurrency */
      baseCurrency: string;
      /** Credentialref */
      credentialRef: string | null;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Environment */
      environment: string;
      /** Name */
      name: string;
      /** Status */
      status: string;
      /** Venuecode */
      venueCode: string;
      /** Venueid */
      venueId: string;
    };
    /** AccountRiskSnapshotResponse */
    AccountRiskSnapshotResponse: {
      /** Accountid */
      accountId: string;
      /**
       * Asof
       * Format: date-time
       */
      asOf: string;
      /** Assetbreakdown */
      assetBreakdown?: components['schemas']['AssetBreakdownResponse'][];
      /** Assetoverviewasof */
      assetOverviewAsOf?: string | null;
      /**
       * Assetoverviewquality
       * @default unavailable
       */
      assetOverviewQuality: string;
      /**
       * Assetscope
       * @default unspecified
       */
      assetScope: string;
      /** Currency */
      currency: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Equity */
      equity?: string | null;
      /** Freemargin */
      freeMargin?: string | null;
      /** Maintenancemargin */
      maintenanceMargin?: string | null;
      /** Margin */
      margin?: string | null;
      /** Marginbalance */
      marginBalance?: string | null;
      /** Marginlevel */
      marginLevel?: string | null;
      /** Totalassets */
      totalAssets?: string | null;
      /** Unrealizedpnl */
      unrealizedPnl?: string | null;
      /** Walletbalance */
      walletBalance?: string | null;
    };
    /** AssetBreakdownResponse */
    AssetBreakdownResponse: {
      /** Accounttype */
      accountType: string;
      /**
       * Categories
       * @default []
       */
      categories: components['schemas']['AssetCategoryResponse'][];
      /** Totalequity */
      totalEquity: string | null;
      /** Valuationcurrency */
      valuationCurrency: string | null;
    } & {
      [key: string]: unknown;
    };
    /** AssetCategoryResponse */
    AssetCategoryResponse: {
      /** Category */
      category: string;
      /** Equity */
      equity: string | null;
    } & {
      [key: string]: unknown;
    };
    /** BalanceSnapshotResponse */
    BalanceSnapshotResponse: {
      /** Accountid */
      accountId: string;
      /**
       * Asof
       * Format: date-time
       */
      asOf: string;
      /** Availablebalance */
      availableBalance?: string | null;
      /** Currency */
      currency: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Equity */
      equity: string;
      /** Snapshotid */
      snapshotId: string;
      /** Source */
      source: string;
    };
    /** BatchLegRequest */
    BatchLegRequest: {
      /** Accountid */
      accountId?: string | null;
      /** Instrumentid */
      instrumentId: string;
      /**
       * Ordertype
       * @enum {string}
       */
      orderType: 'market' | 'limit';
      /** Price */
      price?: string | null;
      /** Quantity */
      quantity: string;
      /** Role */
      role: string;
      /**
       * Side
       * @enum {string}
       */
      side: 'buy' | 'sell';
      /** Symbol */
      symbol: string;
    };
    /** BatchLegResponse */
    BatchLegResponse: {
      /** Accountid */
      accountId?: string | null;
      /** Failurereason */
      failureReason?: string | null;
      /** Orderid */
      orderId?: string | null;
      /** Role */
      role: string;
      /** Status */
      status: string;
    };
    /** BatchRiskResponse */
    BatchRiskResponse: {
      /** Batchid */
      batchId: string;
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /**
       * Failureaction
       * @enum {string}
       */
      failureAction: 'hold_and_escalate' | 'auto_flatten';
      /** Firstfillat */
      firstFillAt?: string | null;
      /** Lastlegat */
      lastLegAt?: string | null;
      /** Maxlegdelayseconds */
      maxLegDelaySeconds: number;
      /** Maxresidualnotional */
      maxResidualNotional: string;
      /** Residualcurrency */
      residualCurrency: string;
      /** Residualexposurenotional */
      residualExposureNotional: string;
      /** Riskreason */
      riskReason?: string | null;
      /**
       * Riskstatus
       * @enum {string}
       */
      riskStatus:
        | 'clear'
        | 'residual_exposure'
        | 'disposition_in_progress'
        | 'resolved'
        | 'escalated';
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** CoinBalanceResponse */
    CoinBalanceResponse: {
      /** Availablebalance */
      availableBalance: string | null;
      /** Currency */
      currency: string;
      /** Equity */
      equity: string;
      /** Usdvalue */
      usdValue: string | null;
      /** Walletbalance */
      walletBalance: string | null;
    } & {
      [key: string]: unknown;
    };
    /** ContractSpecificationResponse */
    ContractSpecificationResponse: {
      /** Contractmultiplier */
      contractMultiplier: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Minorderquantity */
      minOrderQuantity: string;
      /** Pricetick */
      priceTick: string;
      /** Quantitystep */
      quantityStep: string;
      /** Version */
      version: string;
    };
    /** CreateExecutionBatchRequest */
    CreateExecutionBatchRequest: {
      /** Accountid */
      accountId?: string | null;
      /** Direction */
      direction: string;
      /** Idempotencykey */
      idempotencyKey?: string | null;
      /** Legs */
      legs: components['schemas']['BatchLegRequest'][];
      /** Strategyinstanceid */
      strategyInstanceId?: string | null;
      /** Strategykey */
      strategyKey: string;
    };
    /** CreateInternalCapitalTransferRequest */
    CreateInternalCapitalTransferRequest: {
      /** Amount */
      amount: string;
      /**
       * Direction
       * @enum {string}
       */
      direction: 'bybit_to_mt5' | 'mt5_to_bybit';
      /** Idempotencykey */
      idempotencyKey: string;
    };
    /** CreateOrderRequest */
    CreateOrderRequest: {
      /** Accountid */
      accountId: string;
      /** Instrumentid */
      instrumentId: string;
      /**
       * Ordertype
       * @enum {string}
       */
      orderType: 'market' | 'limit';
      /** Price */
      price?: string | null;
      /** Quantity */
      quantity: string;
      /**
       * Side
       * @enum {string}
       */
      side: 'buy' | 'sell';
      /** Symbol */
      symbol: string;
    };
    /** CreateStrategyInstructionRequest */
    CreateStrategyInstructionRequest: {
      action: components['schemas']['StrategyInstructionAction'];
      /** Idempotencykey */
      idempotencyKey: string;
      /** Parameters */
      parameters: {
        [key: string]: unknown;
      };
      /** Positiongroupid */
      positionGroupId?: string | null;
      /** Reason */
      reason?: string | null;
    };
    /** CreateStrategyRunRequest */
    CreateStrategyRunRequest: {
      /** Direction */
      direction: string;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Legs */
      legs: components['schemas']['BatchLegRequest'][];
      /** Reason */
      reason?: string | null;
    };
    /** CreateTradeCommandRequest */
    CreateTradeCommandRequest: {
      /** Accountid */
      accountId: string;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Instrumentid */
      instrumentId: string;
      /**
       * Ordertype
       * @enum {string}
       */
      orderType: 'market' | 'limit';
      /** Price */
      price?: string | null;
      /** Quantity */
      quantity: string;
      /**
       * Side
       * @enum {string}
       */
      side: 'buy' | 'sell';
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Symbol */
      symbol: string;
    };
    /** CredentialReferenceResponse */
    CredentialReferenceResponse: {
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Credentialid */
      credentialId: string;
      /** Credentialref */
      credentialRef: string;
      /** Environment */
      environment: string;
      /** Purpose */
      purpose: string;
      /** Status */
      status: string;
      /** Venuecode */
      venueCode: string;
      /** Venueid */
      venueId: string;
    };
    /** CredentialRotationResponse */
    CredentialRotationResponse: {
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Credentialref */
      credentialRef: string;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Provider */
      provider: string;
      /** Reason */
      reason: string;
      /**
       * Rotatedat
       * Format: date-time
       */
      rotatedAt: string;
      /** Rotatedby */
      rotatedBy: string;
      /** Rotationid */
      rotationId: string;
      /** Version */
      version: string;
    };
    /** CrossSpreadAbnormalOrderResponse */
    CrossSpreadAbnormalOrderResponse: {
      /**
       * Action
       * @default reconcile
       * @enum {string}
       */
      action: 'finish_mt5' | 'close_group' | 'flatten_open' | 'reconcile';
      /** Batchid */
      batchId: string;
      /**
       * Bybitclosefilledquantity
       * @default 0
       */
      bybitCloseFilledQuantity: string;
      /** Bybitremainingquantity */
      bybitRemainingQuantity?: string | null;
      /** Closequantityoz */
      closeQuantityOz?: string | null;
      /** Direction */
      direction: string;
      /** Label */
      label: string;
      /**
       * Mt5Closefilledquantity
       * @default 0
       */
      mt5CloseFilledQuantity: string;
      /** Mt5Pendingclosequantity */
      mt5PendingCloseQuantity?: string | null;
      /** Mt5Positionid */
      mt5PositionId?: string | null;
      /** Mt5Remainingquantity */
      mt5RemainingQuantity?: string | null;
      /** Planid */
      planId?: string | null;
      /** Reason */
      reason?: string | null;
      /** Recoveryidempotencykey */
      recoveryIdempotencyKey?: string | null;
    };
    /** CrossSpreadCloseResult */
    CrossSpreadCloseResult: {
      executionBatch: components['schemas']['ExecutionBatchResponse'];
      exitPlan: components['schemas']['CrossSpreadExitPlanResponse'];
      limitExecution?: components['schemas']['CrossSpreadLimitExecutionResponse'] | null;
      orderIntent?: components['schemas']['CrossSpreadOrderIntentResponse'] | null;
    };
    /** CrossSpreadExitEvaluationResponse */
    CrossSpreadExitEvaluationResponse: {
      /** Evaluatedcount */
      evaluatedCount: number;
      /** Skippedreason */
      skippedReason?: string | null;
      /** Triggeredcount */
      triggeredCount: number;
    };
    /** CrossSpreadExitPlanResponse */
    CrossSpreadExitPlanResponse: {
      /** Closebatchid */
      closeBatchId?: string | null;
      /** Closedat */
      closedAt?: string | null;
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /**
       * Direction
       * @enum {string}
       */
      direction: 'LONG_SPREAD' | 'SHORT_SPREAD';
      /** Entryspread */
      entrySpread: string;
      /** Mt5Positionid */
      mt5PositionId: string;
      /** Openbatchid */
      openBatchId: string;
      /** Originlabel */
      originLabel?: string | null;
      /** Planid */
      planId: string;
      /** Quantityoz */
      quantityOz: string;
      /**
       * Status
       * @enum {string}
       */
      status: 'active' | 'triggered' | 'closing' | 'closed' | 'manual_intervention';
      /**
       * Stoplossexecutionmode
       * @default market
       * @enum {string}
       */
      stopLossExecutionMode: 'market' | 'limit';
      /**
       * Stoplosslimitstrategy
       * @default fok
       * @enum {string}
       */
      stopLossLimitStrategy: 'fok' | 'post_only_chase';
      /** Stoplossspread */
      stopLossSpread?: string | null;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /**
       * Takeprofitexecutionmode
       * @default market
       * @enum {string}
       */
      takeProfitExecutionMode: 'market' | 'limit';
      /**
       * Takeprofitlimitstrategy
       * @default fok
       * @enum {string}
       */
      takeProfitLimitStrategy: 'fok' | 'post_only_chase';
      /** Takeprofitspread */
      takeProfitSpread?: string | null;
      /** Triggerreason */
      triggerReason?: string | null;
      /** Triggerspread */
      triggerSpread?: string | null;
      /** Triggeredat */
      triggeredAt?: string | null;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /**
     * CrossSpreadExitPlanUpdateRequest
     * @description Editable trigger settings for an already-open, still active plan.
     */
    CrossSpreadExitPlanUpdateRequest: {
      /** Stoplossexecutionmode */
      stopLossExecutionMode?: ('market' | 'limit') | null;
      /** Stoplosslimitstrategy */
      stopLossLimitStrategy?: ('fok' | 'post_only_chase') | null;
      /** Stoplossspread */
      stopLossSpread?: string | null;
      /** Takeprofitexecutionmode */
      takeProfitExecutionMode?: ('market' | 'limit') | null;
      /** Takeprofitlimitstrategy */
      takeProfitLimitStrategy?: ('fok' | 'post_only_chase') | null;
      /** Takeprofitspread */
      takeProfitSpread?: string | null;
    };
    /** CrossSpreadHistoryPointResponse */
    CrossSpreadHistoryPointResponse: {
      /**
       * Asof
       * Format: date-time
       */
      asOf: string;
      /** Bybitmid */
      bybitMid?: string | null;
      /** Longspread */
      longSpread?: string | null;
      /** Mt5Mid */
      mt5Mid?: string | null;
      /** Shortspread */
      shortSpread?: string | null;
    };
    /** CrossSpreadLeverageRequest */
    CrossSpreadLeverageRequest: {
      /** Leverage */
      leverage: string;
    };
    /** CrossSpreadLeverageResponse */
    CrossSpreadLeverageResponse: {
      /** Accountid */
      accountId: string;
      /** Leverage */
      leverage: string | null;
      /** Source */
      source: string;
      /** Symbol */
      symbol: string;
    } & {
      [key: string]: unknown;
    };
    /** CrossSpreadLimitExecutionResponse */
    CrossSpreadLimitExecutionResponse: {
      /** Bybitlimitprice */
      bybitLimitPrice: string;
      /** Bybitticksize */
      bybitTickSize: string;
      /** Currentlyexecutable */
      currentlyExecutable: boolean;
      /**
       * Direction
       * @enum {string}
       */
      direction: 'BUY_BYBIT_SELL_MT5' | 'SELL_BYBIT_BUY_MT5';
      /** Executablespread */
      executableSpread: string;
      /** Hedgereserve */
      hedgeReserve: string;
      /** Limitspread */
      limitSpread: string;
      /**
       * Limitstrategy
       * @enum {string}
       */
      limitStrategy: 'fok' | 'post_only_chase';
      /** Mt5Referenceprice */
      mt5ReferencePrice: string;
      /** Rawbybitlimitprice */
      rawBybitLimitPrice: string;
      /**
       * Timeinforce
       * @enum {string}
       */
      timeInForce: 'FOK' | 'PostOnly';
    };
    /** CrossSpreadMarketCloseRequest */
    CrossSpreadMarketCloseRequest: {
      /**
       * Executionmode
       * @default market
       * @enum {string}
       */
      executionMode: 'market' | 'limit';
      /** Idempotencykey */
      idempotencyKey?: string | null;
      /** Limitspread */
      limitSpread?: string | null;
      /**
       * Limitstrategy
       * @default fok
       * @enum {string}
       */
      limitStrategy: 'fok' | 'post_only_chase';
      /** Quantityoz */
      quantityOz?: string | null;
    };
    /** CrossSpreadMarketCommandRequest */
    CrossSpreadMarketCommandRequest: {
      /**
       * Action
       * @enum {string}
       */
      action: 'OPEN_LONG' | 'CLOSE_LONG' | 'OPEN_SHORT' | 'CLOSE_SHORT';
      /** Idempotencykey */
      idempotencyKey?: string | null;
      /** Quantityoz */
      quantityOz: string;
    };
    /** CrossSpreadMarketOpenRequest */
    CrossSpreadMarketOpenRequest: {
      /**
       * Direction
       * @enum {string}
       */
      direction: 'LONG_SPREAD' | 'SHORT_SPREAD';
      /**
       * Executionmode
       * @default market
       * @enum {string}
       */
      executionMode: 'market' | 'limit';
      /** Idempotencykey */
      idempotencyKey?: string | null;
      /** Limitspread */
      limitSpread?: string | null;
      /**
       * Limitstrategy
       * @default fok
       * @enum {string}
       */
      limitStrategy: 'fok' | 'post_only_chase';
      /** Quantityoz */
      quantityOz: string;
      /**
       * Stoplossexecutionmode
       * @default market
       * @enum {string}
       */
      stopLossExecutionMode: 'market' | 'limit';
      /**
       * Stoplosslimitstrategy
       * @default fok
       * @enum {string}
       */
      stopLossLimitStrategy: 'fok' | 'post_only_chase';
      /** Stoplossspread */
      stopLossSpread?: string | null;
      /**
       * Takeprofitexecutionmode
       * @default market
       * @enum {string}
       */
      takeProfitExecutionMode: 'market' | 'limit';
      /**
       * Takeprofitlimitstrategy
       * @default fok
       * @enum {string}
       */
      takeProfitLimitStrategy: 'fok' | 'post_only_chase';
      /** Takeprofitspread */
      takeProfitSpread?: string | null;
    };
    /** CrossSpreadMetricsResponse */
    CrossSpreadMetricsResponse: {
      /** Buyerinventoryfee */
      buyerInventoryFee?: string | null;
      /** Fundingrate */
      fundingRate?: string | null;
      /** Sellerinventoryfee */
      sellerInventoryFee?: string | null;
      /** Usdtusd */
      usdtUsd?: string | null;
    };
    /** CrossSpreadObservabilityResponse */
    CrossSpreadObservabilityResponse: {
      /**
       * Asof
       * Format: date-time
       */
      asOf: string;
      bybit: components['schemas']['CrossSpreadVenueObservabilityResponse'];
      /** Historyhours */
      historyHours: number;
      mt5: components['schemas']['CrossSpreadVenueObservabilityResponse'];
      /**
       * Status
       * @enum {string}
       */
      status: 'complete' | 'partial' | 'unavailable';
      /** Warnings */
      warnings: string[];
    };
    /** CrossSpreadOpenResult */
    CrossSpreadOpenResult: {
      executionBatch: components['schemas']['ExecutionBatchResponse'];
      exitPlan?: components['schemas']['CrossSpreadExitPlanResponse'] | null;
      limitExecution?: components['schemas']['CrossSpreadLimitExecutionResponse'] | null;
      orderIntent?: components['schemas']['CrossSpreadOrderIntentResponse'] | null;
    };
    /** CrossSpreadOrderIntentResponse */
    CrossSpreadOrderIntentResponse: {
      /**
       * Action
       * @enum {string}
       */
      action: 'OPEN_LONG_SPREAD' | 'CLOSE_LONG_SPREAD' | 'OPEN_SHORT_SPREAD' | 'CLOSE_SHORT_SPREAD';
      /**
       * Direction
       * @enum {string}
       */
      direction: 'LONG_SPREAD' | 'SHORT_SPREAD';
      /**
       * Executiontype
       * @enum {string}
       */
      executionType: 'MARKET' | 'LIMIT';
      /** Isopen */
      isOpen: boolean;
      /**
       * Triggerreason
       * @enum {string}
       */
      triggerReason:
        | 'MANUAL'
        | 'STRATEGY'
        | 'TAKE_PROFIT'
        | 'STOP_LOSS'
        | 'KILL_SWITCH'
        | 'RISK_REDUCTION';
    };
    /** CrossSpreadPositionOverviewResponse */
    CrossSpreadPositionOverviewResponse: {
      /** Abnormalorders */
      abnormalOrders: components['schemas']['CrossSpreadAbnormalOrderResponse'][];
      /**
       * Asof
       * Format: date-time
       */
      asOf: string;
      /** Bybitpnlusdt */
      bybitPnlUsdt: string | null;
      /**
       * Dataqualitystate
       * @enum {string}
       */
      dataQualityState: 'complete' | 'partial' | 'unavailable';
      /** Groups */
      groups: components['schemas']['CrossSpreadPositionPnlResponse'][];
      /** Mt5Pnlusdt */
      mt5PnlUsdt: string | null;
      /** Totalpnlusdt */
      totalPnlUsdt: string | null;
      /** Unattributedpositions */
      unattributedPositions: components['schemas']['CrossSpreadUnattributedPositionResponse'][];
    };
    /** CrossSpreadPositionPnlResponse */
    CrossSpreadPositionPnlResponse: {
      /** Bybitentryprice */
      bybitEntryPrice: string | null;
      /** Bybitpnlusdt */
      bybitPnlUsdt: string | null;
      /** Bybitquantity */
      bybitQuantity: string | null;
      /**
       * Dataqualitystate
       * @enum {string}
       */
      dataQualityState: 'complete' | 'partial' | 'unavailable';
      /**
       * Direction
       * @default
       */
      direction: string;
      /** Mt5Entryprice */
      mt5EntryPrice: string | null;
      /** Mt5Pnlusdt */
      mt5PnlUsdt: string | null;
      /** Mt5Positionid */
      mt5PositionId: string | null;
      /** Mt5Quantity */
      mt5Quantity: string | null;
      /**
       * Opentime
       * Format: date-time
       */
      openTime: string;
      /** Planid */
      planId: string;
      /**
       * Planupdatedat
       * Format: date-time
       */
      planUpdatedAt: string;
      /** Quantityoz */
      quantityOz: string;
      /** Reason */
      reason: string | null;
      /** Totalpnlusdt */
      totalPnlUsdt: string | null;
    };
    /** CrossSpreadPreflightRequest */
    CrossSpreadPreflightRequest: {
      /**
       * Action
       * @enum {string}
       */
      action: 'OPEN_LONG' | 'CLOSE_LONG' | 'OPEN_SHORT' | 'CLOSE_SHORT';
      /** Exitplanid */
      exitPlanId?: string | null;
      /** Quantityoz */
      quantityOz: string;
    };
    /** CrossSpreadPreflightResponse */
    CrossSpreadPreflightResponse: {
      /** Preparedat */
      preparedAt: string;
      /**
       * Status
       * @constant
       */
      status: 'ready';
    };
    /** CrossSpreadSnapshotResponse */
    CrossSpreadSnapshotResponse: {
      /**
       * Asof
       * Format: date-time
       */
      asOf: string;
      bybit: components['schemas']['CrossSpreadVenueSnapshotResponse'];
      /** Longspread */
      longSpread?: string | null;
      metrics?: components['schemas']['CrossSpreadMetricsResponse'];
      mt5: components['schemas']['CrossSpreadVenueSnapshotResponse'];
      positionOverview?: components['schemas']['CrossSpreadPositionOverviewResponse'] | null;
      /** Shortspread */
      shortSpread?: string | null;
      /** Status */
      status: string;
    };
    /** CrossSpreadUnattributedPositionResponse */
    CrossSpreadUnattributedPositionResponse: {
      /** Accountid */
      accountId?: string | null;
      /** Asof */
      asOf?: string | null;
      /** Averageprice */
      averagePrice?: string | null;
      /** Currency */
      currency?: string | null;
      /** Externalid */
      externalId?: string | null;
      /** Quantity */
      quantity: string;
      /** Side */
      side: string;
      /** Symbol */
      symbol: string;
      /** Unrealizedpnl */
      unrealizedPnl?: string | null;
      /**
       * Venue
       * @enum {string}
       */
      venue: 'bybit' | 'mt5';
    };
    /** CrossSpreadVenueObservabilityResponse */
    CrossSpreadVenueObservabilityResponse: {
      /** Accountid */
      accountId: string;
      accountRisk: components['schemas']['VenueAccountRiskSnapshotResponse'] | null;
      /** Activeorders */
      activeOrders: components['schemas']['VenueOrderSnapshotResponse'][];
      /** Positions */
      positions: components['schemas']['VenuePositionSnapshotResponse'][];
      /** Recentfills */
      recentFills: components['schemas']['VenueFillSnapshotResponse'][];
      /** Recentorders */
      recentOrders: components['schemas']['VenueOrderSnapshotResponse'][];
      /** Sectionstates */
      sectionStates: {
        [key: string]: 'complete' | 'unavailable';
      };
      /**
       * Status
       * @enum {string}
       */
      status: 'complete' | 'partial' | 'unavailable';
      /** Symbol */
      symbol: string;
      /** Venue */
      venue: string;
      /** Warnings */
      warnings: string[];
    };
    /** CrossSpreadVenueSnapshotResponse */
    CrossSpreadVenueSnapshotResponse: {
      /** Asof */
      asOf?: string | null;
      /** Fetchlatencyms */
      fetchLatencyMs?: number | null;
      /**
       * Positions
       * @default []
       */
      positions: components['schemas']['VenuePositionResponse'][];
      quote?: components['schemas']['MarketQuoteResponse'] | null;
      /** Reason */
      reason?: string | null;
      /** Status */
      status: string;
      /** Symbol */
      symbol: string;
      /** Venue */
      venue: string;
    };
    /** EconomicEventResponse */
    EconomicEventResponse: {
      /** Accountid */
      accountId: string | null;
      /** Amount */
      amount: string;
      /** Batchid */
      batchId: string | null;
      /** Currency */
      currency: string;
      /** Eventtype */
      eventType: string;
      /** Externaleventid */
      externalEventId: string;
      /** Externalorderid */
      externalOrderId: string | null;
      /** Instructionid */
      instructionId: string | null;
      /** Occurredat */
      occurredAt: string;
      /** Orderid */
      orderId: string | null;
      /** Source */
      source: string | null;
      /** Symbol */
      symbol: string | null;
    } & {
      [key: string]: unknown;
    };
    /** EquityHistoryPoint */
    EquityHistoryPoint: {
      /** Asof */
      asOf: string;
      /** Equity */
      equity: string;
    };
    /** ExchangeConnectivityResponse */
    ExchangeConnectivityResponse: {
      /**
       * Configuredcredentialcount
       * @default 0
       */
      configuredCredentialCount: number;
      /**
       * Credentialcount
       * @default 0
       */
      credentialCount: number;
      /**
       * Credentials
       * @default []
       */
      credentials: components['schemas']['ExchangeCredentialInspectionResponse'][];
      /** Gateway */
      gateway?: string | null;
      /** Status */
      status: string;
    };
    /** ExchangeCredentialInspectionResponse */
    ExchangeCredentialInspectionResponse: {
      /** Availablefields */
      availableFields: string[];
      /** Configured */
      configured: boolean;
      /** Credentialref */
      credentialRef: string;
      /** Envprefix */
      envPrefix: string;
      /** Missingfields */
      missingFields: string[];
    };
    /** ExchangeVenueReadinessResponse */
    ExchangeVenueReadinessResponse: {
      /** Status */
      status: string;
      /**
       * Venues
       * @default []
       */
      venues: components['schemas']['ExchangeVenueReadinessResult'][];
    };
    /** ExchangeVenueReadinessResult */
    ExchangeVenueReadinessResult: {
      /**
       * Checks
       * @default []
       */
      checks: string[];
      /** Credentialref */
      credentialRef: string;
      /** Markettype */
      marketType?: string | null;
      /** Reason */
      reason?: string | null;
      /** Status */
      status: string;
      /** Symbol */
      symbol: string;
      /** Venue */
      venue: string;
    };
    /** ExecutionBatchResponse */
    ExecutionBatchResponse: {
      /** Accountid */
      accountId?: string | null;
      /** Batchid */
      batchId: string;
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Direction */
      direction: string;
      /** Failurereason */
      failureReason?: string | null;
      /** Idempotencykey */
      idempotencyKey?: string | null;
      /** Legs */
      legs: components['schemas']['BatchLegResponse'][];
      /** Requiresmanualintervention */
      requiresManualIntervention: boolean;
      /**
       * Status
       * @enum {string}
       */
      status:
        | 'pending'
        | 'executing'
        | 'partially_executed'
        | 'hedged'
        | 'completed'
        | 'failed'
        | 'manual_intervention';
      /** Strategyinstanceid */
      strategyInstanceId?: string | null;
      /** Strategykey */
      strategyKey: string;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** ExecutionRiskPolicyResponse */
    ExecutionRiskPolicyResponse: {
      /** Actor */
      actor: string;
      /**
       * Failureaction
       * @enum {string}
       */
      failureAction: 'hold_and_escalate' | 'auto_flatten';
      /** Maxlegdelayseconds */
      maxLegDelaySeconds: number;
      /** Maxresidualnotional */
      maxResidualNotional: string;
      /**
       * Source
       * @enum {string}
       */
      source: 'default' | 'configured';
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** ExecutionRiskPolicyUpdateRequest */
    ExecutionRiskPolicyUpdateRequest: {
      /** Actor */
      actor: string;
      /**
       * Failureaction
       * @enum {string}
       */
      failureAction: 'hold_and_escalate' | 'auto_flatten';
      /** Idempotencykey */
      idempotencyKey: string;
      /** Maxlegdelayseconds */
      maxLegDelaySeconds: number;
      /** Maxresidualnotional */
      maxResidualNotional: string;
    };
    /** FillResponse */
    FillResponse: {
      /** Accountid */
      accountId: string;
      /** Action */
      action?: string | null;
      /** Batchid */
      batchId?: string | null;
      /** Currency */
      currency?: string | null;
      /** Direction */
      direction?: string | null;
      /** Externalfillid */
      externalFillId?: string | null;
      /** Externalorderid */
      externalOrderId?: string | null;
      /** Fee */
      fee?: string | null;
      /** Fillid */
      fillId: string;
      /** Instructionid */
      instructionId?: string | null;
      /** Instrumentid */
      instrumentId: string;
      /**
       * Occurredat
       * Format: date-time
       */
      occurredAt: string;
      /** Orderconfirmedat */
      orderConfirmedAt?: string | null;
      /** Orderid */
      orderId: string;
      /**
       * Origin
       * @default legacy
       */
      origin: string;
      /** Price */
      price: string;
      /** Quantity */
      quantity: string;
      /** Realizedpnl */
      realizedPnl?: string | null;
      /** Side */
      side: string;
      /** Source */
      source?: string | null;
      /** Swap */
      swap?: string | null;
      /** Symbol */
      symbol?: string | null;
      /**
       * Timequality
       * @default legacy
       */
      timeQuality: string;
    };
    /** FinancialAmountsResponse */
    FinancialAmountsResponse: {
      /**
       * Accountid
       * @default
       */
      accountId: string;
      /** Currency */
      currency: string;
      /** Fees */
      fees: string | null;
      /** Fundingpnl */
      fundingPnl: string | null;
      /** Netpnl */
      netPnl: string | null;
      /** Realizedpnl */
      realizedPnl: string | null;
      /** Swappnl */
      swapPnl: string | null;
      /** Tradingpnl */
      tradingPnl: string | null;
    } & {
      [key: string]: unknown;
    };
    /** FinancialCoverageResponse */
    FinancialCoverageResponse: {
      /** Accountid */
      accountId: string;
      /** Asof */
      asOf: string;
      /** Historyend */
      historyEnd: string | null;
      /** Historystart */
      historyStart: string | null;
    } & {
      [key: string]: unknown;
    };
    /** FinancialProjectionRebuildResponse */
    FinancialProjectionRebuildResponse: {
      /**
       * Completedat
       * Format: date-time
       */
      completedAt: string;
      /** Factcount */
      factCount: number;
      /** Rebuiltpaircount */
      rebuiltPairCount: number;
      /** Strategyinstanceid */
      strategyInstanceId: string;
    };
    /** FinancialTimelinePointResponse */
    FinancialTimelinePointResponse: {
      /** Accountid */
      accountId: string;
      /** Asof */
      asOf: string;
      /** Currency */
      currency: string;
      /** Realizedpnl */
      realizedPnl: string;
    } & {
      [key: string]: unknown;
    };
    /** FormalNavSnapshotResponse */
    FormalNavSnapshotResponse: {
      /** Capitalbase */
      capitalBase: string;
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Currency */
      currency: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Equity */
      equity?: string | null;
      /** Includedaccountcount */
      includedAccountCount: number;
      /** Missingaccountids */
      missingAccountIds: string[];
      /** Nav */
      nav?: string | null;
      /** Requiredaccountcount */
      requiredAccountCount: number;
      /** Snapshotid */
      snapshotId: string;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /**
       * Valuationtime
       * Format: date-time
       */
      valuationTime: string;
    };
    /** FormalPnlResponse */
    FormalPnlResponse: {
      /** Accountid */
      accountId: string;
      /** Cfdspreadpnl */
      cfdSpreadPnl?: string | null;
      /** Cumulativecommission */
      cumulativeCommission?: string | null;
      /** Cumulativeslippagecost */
      cumulativeSlippageCost?: string | null;
      /** Currency */
      currency: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Factcount */
      factCount: number;
      /** Feepnl */
      feePnl: string;
      /** Fundingpnl */
      fundingPnl: string;
      /** Fxpnl */
      fxPnl: string;
      /** Instrumentid */
      instrumentId: string;
      /** Perpetualbasispnl */
      perpetualBasisPnl?: string | null;
      /** Pnlattributionresidual */
      pnlAttributionResidual?: string | null;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Swappnl */
      swapPnl: string;
      /** Tokenbasispnl */
      tokenBasisPnl?: string | null;
      /** Totalpnl */
      totalPnl: string;
      /** Totalspreadchangepnl */
      totalSpreadChangePnl?: string | null;
      /** Tradingpnl */
      tradingPnl: string;
      /** Ufxpnl */
      uFxPnl?: string | null;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** FormalPositionResponse */
    FormalPositionResponse: {
      /** Accountid */
      accountId: string;
      /** Averageprice */
      averagePrice?: string | null;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Instrumentid */
      instrumentId: string;
      /** Netquantity */
      netQuantity: string;
      /** Quantityunit */
      quantityUnit: string;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** FundingActiveReservation */
    FundingActiveReservation: {
      /** Activereserved */
      activeReserved: string;
      /** Crossreserved */
      crossReserved: string;
      /** Currency */
      currency: string;
      /** Fundingavailable */
      fundingAvailable: string | null;
      /** Fundingreserved */
      fundingReserved: string;
    };
    /** FundingBalanceQuote */
    FundingBalanceQuote: {
      /** Amount */
      amount: string | null;
      /** Asof */
      asOf: string | null;
      /** Currency */
      currency: string;
      /**
       * Dataqualitystate
       * @enum {string}
       */
      dataQualityState: 'complete' | 'unavailable';
      /** Reason */
      reason?: string | null;
    };
    /** FundingExecutionContextResponse */
    FundingExecutionContextResponse: {
      /** Accountid */
      accountId: string;
      activeReservation: components['schemas']['FundingActiveReservation'];
      /** Asof */
      asOf: string;
      /** Availablebalance */
      availableBalance: {
        [key: string]: unknown;
      } | null;
      /** Basis */
      basis: string | null;
      /** Contractmultiplier */
      contractMultiplier: {
        [key: string]: string;
      };
      /** Controlledlivereadiness */
      controlledLiveReadiness: {
        [key: string]: unknown;
      };
      /** Dataqualitystate */
      dataQualityState: string;
      /** Fundingrate */
      fundingRate: string | null;
      /** Minimumquantity */
      minimumQuantity: {
        [key: string]: string;
      };
      /** Nextfundingtime */
      nextFundingTime: string | null;
      openSizing?: components['schemas']['FundingOpenSizingResponse'] | null;
      /** Perpetualquote */
      perpetualQuote: {
        [key: string]: unknown;
      };
      /** Perpetualsymbol */
      perpetualSymbol: string;
      /** Quantitystep */
      quantityStep: {
        [key: string]: string;
      };
      /** Requestednotional */
      requestedNotional: string | null;
      /** Runtime */
      runtime: {
        [key: string]: unknown;
      };
      /** Sharedresourceclaims */
      sharedResourceClaims: {
        [key: string]: unknown;
      }[];
      /** Spotquote */
      spotQuote: {
        [key: string]: unknown;
      };
      /** Spotsymbol */
      spotSymbol: string;
      /** Suggestedquantity */
      suggestedQuantity: string | null;
      /** Symboloptions */
      symbolOptions: components['schemas']['FundingSymbolOption'][];
      /** Ticksize */
      tickSize: {
        [key: string]: string;
      };
      /** Venue */
      venue: string;
    };
    /** FundingInstructionRequest */
    FundingInstructionRequest: {
      /**
       * Action
       * @enum {string}
       */
      action: 'open' | 'close';
      /**
       * Executionpolicy
       * @default post_only_chase
       * @enum {string}
       */
      executionPolicy: 'market' | 'fok' | 'post_only_chase';
      /** Expectedperpetualquantity */
      expectedPerpetualQuantity?: string | null;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Perpetuallimitprice */
      perpetualLimitPrice?: string | null;
      /** Perpetualsymbol */
      perpetualSymbol: string;
      /** Quantity */
      quantity: string;
      /** Spotsymbol */
      spotSymbol: string;
      /** Targetopeninstructionid */
      targetOpenInstructionId?: string | null;
    };
    /** FundingMarketCommandRequest */
    FundingMarketCommandRequest: {
      /**
       * Action
       * @enum {string}
       */
      action: 'OPEN_SHORT_PERP_LONG_SPOT' | 'CLOSE_SHORT_PERP_LONG_SPOT';
      /** Idempotencykey */
      idempotencyKey?: string | null;
      /** Perpetualsymbol */
      perpetualSymbol: string;
      /** Quantity */
      quantity: string;
      /** Spotsymbol */
      spotSymbol: string;
    };
    /** FundingOpenSizingResponse */
    FundingOpenSizingResponse: {
      /** Expectedspotnetquantity */
      expectedSpotNetQuantity: string | null;
      /** Perpetualquantity */
      perpetualQuantity: string | null;
      /** Reason */
      reason: string | null;
      /** Roundingresidualquantity */
      roundingResidualQuantity: string | null;
      /** Spotbasefeerate */
      spotBaseFeeRate: string;
      /** Spotquantity */
      spotQuantity: string | null;
      /** Valid */
      valid: boolean;
    };
    /** FundingPositionGroupResponse */
    FundingPositionGroupResponse: {
      /**
       * Abnormalaction
       * @default reconcile
       * @enum {string}
       */
      abnormalAction: 'close_group' | 'flatten_open' | 'reconcile';
      /** Abnormalreason */
      abnormalReason?: string | null;
      /** Alreadyclosedquantity */
      alreadyClosedQuantity: string;
      /** Asof */
      asOf: string;
      /** Authoritativeclosedquantity */
      authoritativeClosedQuantity: string;
      /** Batchid */
      batchId: string;
      /** Cumulativeperpetualfill */
      cumulativePerpetualFill: string;
      /** Cumulativespotfill */
      cumulativeSpotFill: string;
      /** Fees */
      fees: string | null;
      /** Fundingfees */
      fundingFees: string | null;
      /** Hedgedquantity */
      hedgedQuantity: string;
      /** Instructionid */
      instructionId: string;
      /**
       * Isabnormal
       * @default false
       */
      isAbnormal: boolean;
      /**
       * Lifecyclestate
       * @enum {string}
       */
      lifecycleState: 'active' | 'history';
      /** Netdeltaquantity */
      netDeltaQuantity: string | null;
      /** Netspotacquired */
      netSpotAcquired: string | null;
      /** Openinstructionid */
      openInstructionId: string;
      /** Pendingclosequantity */
      pendingCloseQuantity: string;
      /** Perpetualrequestedquantity */
      perpetualRequestedQuantity: string;
      /** Perpetualside */
      perpetualSide: string;
      /** Perpetualsymbol */
      perpetualSymbol: string;
      /** Pnl */
      pnl: string | null;
      /** Remainingclosablequantity */
      remainingClosableQuantity: string;
      /** Remainingperpetualquantity */
      remainingPerpetualQuantity: string;
      /** Remainingspotholding */
      remainingSpotHolding: string | null;
      /** Remainingspotquantity */
      remainingSpotQuantity: string | null;
      /** Residualquantity */
      residualQuantity: string;
      /** Resultunknownreservedquantity */
      resultUnknownReservedQuantity: string;
      /** Spotfeeadjusted */
      spotFeeAdjusted: boolean;
      /** Spotfeeresidualquantity */
      spotFeeResidualQuantity: string | null;
      /** Spotquantitystep */
      spotQuantityStep: string | null;
      /** Spotrequestedquantity */
      spotRequestedQuantity: string;
      /** Spotside */
      spotSide: string;
      /** Spotsymbol */
      spotSymbol: string;
      /** Status */
      status: string;
      /** Workspacestate */
      workspaceState: {
        [key: string]: unknown;
      };
    };
    /** FundingSymbolOption */
    FundingSymbolOption: {
      /** Baseasset */
      baseAsset: string;
      /** Perpetualinstrumentid */
      perpetualInstrumentId: string;
      /** Perpetualsymbol */
      perpetualSymbol: string;
      /** Quotecurrency */
      quoteCurrency: string;
      /** Spotinstrumentid */
      spotInstrumentId: string;
      /** Spotsymbol */
      spotSymbol: string;
    };
    /** FundingTransferQuoteResponse */
    FundingTransferQuoteResponse: {
      /**
       * Asof
       * Format: date-time
       */
      asOf: string;
      bybitTransferable: components['schemas']['FundingBalanceQuote'];
      /**
       * Mode
       * @enum {string}
       */
      mode: 'automated' | 'unavailable';
      mt5Withdrawable: components['schemas']['FundingBalanceQuote'];
      /** Officialfundingurl */
      officialFundingUrl: string;
      /** Readinessreason */
      readinessReason?: string | null;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Suggestedamount */
      suggestedAmount: string | null;
      /** Suggesteddirection */
      suggestedDirection: ('bybit_to_mt5' | 'mt5_to_bybit') | null;
    };
    /** FundingWorkspaceResponse */
    FundingWorkspaceResponse: {
      /** Executionbatch */
      executionBatch: {
        [key: string]: unknown;
      } | null;
      /** Instruction */
      instruction: {
        [key: string]: unknown;
      };
      /** Workspacestate */
      workspaceState: {
        [key: string]: unknown;
      };
    };
    /** HTTPValidationError */
    HTTPValidationError: {
      /** Detail */
      detail?: components['schemas']['ValidationError'][];
    };
    /** InstrumentResponse */
    InstrumentResponse: {
      /** Basecurrency */
      baseCurrency: string;
      contract?: components['schemas']['ContractSpecificationResponse'] | null;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Instrumentcode */
      instrumentCode: string;
      /** Instrumentid */
      instrumentId: string;
      /** Instrumenttype */
      instrumentType: string;
      /** Name */
      name: string;
      /** Quantityunit */
      quantityUnit: string;
      /** Quotecurrency */
      quoteCurrency: string;
      /** Settlecurrency */
      settleCurrency: string;
    };
    /** InternalCapitalTransferResponse */
    InternalCapitalTransferResponse: {
      /** Amount */
      amount: string;
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Currency */
      currency: string;
      /**
       * Currentlocation
       * @enum {string}
       */
      currentLocation: 'bybit_uta' | 'funding' | 'mt5' | 'unknown';
      /**
       * Direction
       * @enum {string}
       */
      direction: 'bybit_to_mt5' | 'mt5_to_bybit';
      /** Externaltransferid */
      externalTransferId: string | null;
      /** Failurereason */
      failureReason: string | null;
      /** Idempotencykey */
      idempotencyKey: string;
      /**
       * Mode
       * @enum {string}
       */
      mode: 'automated' | 'assisted';
      /** Officialfundingurl */
      officialFundingUrl: string;
      /** Requestedby */
      requestedBy: string;
      /**
       * Status
       * @enum {string}
       */
      status: 'pending' | 'completed' | 'failed' | 'result_unknown';
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Transferid */
      transferId: string;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** LiveTradingSessionApprovalRequest */
    LiveTradingSessionApprovalRequest: {
      /** Reason */
      reason: string;
    };
    /** LiveTradingSessionRequest */
    LiveTradingSessionRequest: {
      /** Accountid */
      accountId: string;
      /**
       * Endsat
       * Format: date-time
       */
      endsAt: string;
      /** Evidencereference */
      evidenceReference: string;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Maxdailynotional */
      maxDailyNotional: string;
      /** Maxordernotional */
      maxOrderNotional: string;
      /** Ordertypes */
      orderTypes: ('market' | 'limit')[];
      /**
       * Readonlyverifiedat
       * Format: date-time
       */
      readOnlyVerifiedAt: string;
      /** Reason */
      reason: string;
      /**
       * Sessiontype
       * @enum {string}
       */
      sessionType: 'minimum_size_acceptance' | 'existing_limits' | 'scale_change';
      /** Sides */
      sides: ('buy' | 'sell')[];
      /**
       * Startsat
       * Format: date-time
       */
      startsAt: string;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Symbols */
      symbols: string[];
    };
    /** LiveTradingSessionResponse */
    LiveTradingSessionResponse: {
      /** Accountid */
      accountId: string;
      /** Applicantuserid */
      applicantUserId: string;
      /** Approvalreason */
      approvalReason?: string | null;
      /** Approvedat */
      approvedAt?: string | null;
      /** Approveruserid */
      approverUserId?: string | null;
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /**
       * Endsat
       * Format: date-time
       */
      endsAt: string;
      /** Evidencereference */
      evidenceReference: string;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Maxdailynotional */
      maxDailyNotional: string;
      /** Maxordernotional */
      maxOrderNotional: string;
      /** Ordertypes */
      orderTypes: string[];
      /**
       * Readonlyverifiedat
       * Format: date-time
       */
      readOnlyVerifiedAt: string;
      /** Reason */
      reason: string;
      /** Revocationreason */
      revocationReason?: string | null;
      /** Revokedat */
      revokedAt?: string | null;
      /** Revokedby */
      revokedBy?: string | null;
      /** Sessionid */
      sessionId: string;
      /**
       * Sessiontype
       * @enum {string}
       */
      sessionType: 'minimum_size_acceptance' | 'existing_limits' | 'scale_change';
      /** Sides */
      sides: string[];
      /**
       * Startsat
       * Format: date-time
       */
      startsAt: string;
      /**
       * Status
       * @enum {string}
       */
      status: 'pending' | 'approved' | 'revoked' | 'expired';
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Symbols */
      symbols: string[];
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** LiveTradingSessionRevocationRequest */
    LiveTradingSessionRevocationRequest: {
      /** Reason */
      reason: string;
    };
    /** MarketQuoteResponse */
    MarketQuoteResponse: {
      /** Ask */
      ask: string;
      /** Bid */
      bid: string;
      /** Currency */
      currency: string;
      /** Last */
      last?: string | null;
      /** Mid */
      mid: string;
    };
    /** OrderDetailResponse */
    OrderDetailResponse: {
      /** Accountid */
      accountId: string;
      /** Action */
      action?: string | null;
      /** Averagefillprice */
      averageFillPrice?: string | null;
      /** Batchid */
      batchId?: string | null;
      /** Cancelreason */
      cancelReason?: string | null;
      /** Commandid */
      commandId: string;
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Direction */
      direction?: string | null;
      /** Externalorderid */
      externalOrderId?: string | null;
      /** Filledquantity */
      filledQuantity?: string | null;
      /** Instructionid */
      instructionId?: string | null;
      /** Instrumentid */
      instrumentId: string;
      /** Orderid */
      orderId: string;
      /** Ordertype */
      orderType: string;
      /** Price */
      price: string | null;
      /** Quantity */
      quantity: string;
      /** Reduceonly */
      reduceOnly?: boolean | null;
      /** Rejectreason */
      rejectReason?: string | null;
      /** Side */
      side: string;
      /** Status */
      status: string;
      /** Symbol */
      symbol: string;
      /** Timeinforce */
      timeInForce?: string | null;
      /**
       * Timequality
       * @default legacy
       */
      timeQuality: string;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** OrderResponse */
    OrderResponse: {
      /** Commandid */
      commandId: string;
      /** Externalorderid */
      externalOrderId?: string | null;
      /** Orderid */
      orderId: string;
      /** Status */
      status: string;
    };
    /** OrderVenueReconciliationResponse */
    OrderVenueReconciliationResponse: {
      /** Commandid */
      commandId: string;
      /** Differenceids */
      differenceIds: string[];
      /** Externalorderid */
      externalOrderId?: string | null;
      /** Importedfactids */
      importedFactIds: string[];
      /** Orderid */
      orderId: string;
      /**
       * Reconciledat
       * Format: date-time
       */
      reconciledAt: string;
      /** Recovered */
      recovered: boolean;
      /** Source */
      source: string;
      /** Statusafter */
      statusAfter: string;
      /** Statusbefore */
      statusBefore: string;
    };
    /** PnlResponse */
    PnlResponse: {
      /** Accountid */
      accountId: string;
      /** Fees */
      fees: string;
      /** Instrumentid */
      instrumentId: string;
      /** Realizedpnl */
      realizedPnl: string;
      /** Tradingpnl */
      tradingPnl: string;
    };
    /** PositionResponse */
    PositionResponse: {
      /** Accountid */
      accountId: string;
      /** Asof */
      asOf?: string | null;
      /** Averageprice */
      averagePrice: string | null;
      /** Category */
      category?: string | null;
      /** Currency */
      currency?: string | null;
      /** Currentprice */
      currentPrice?: string | null;
      /** Externalpositionid */
      externalPositionId?: string | null;
      /** Instrumentid */
      instrumentId: string;
      /** Instrumenttype */
      instrumentType?: string | null;
      /** Liquidationprice */
      liquidationPrice?: string | null;
      /** Netquantity */
      netQuantity: string;
      /** Stoplossprice */
      stopLossPrice?: string | null;
      /** Swap */
      swap?: string | null;
      /** Symbol */
      symbol?: string | null;
      /** Takeprofitprice */
      takeProfitPrice?: string | null;
      /** Unrealizedpnl */
      unrealizedPnl?: string | null;
    };
    /** ReconciliationIssueResponse */
    ReconciliationIssueResponse: {
      /**
       * Detectedat
       * Format: date-time
       */
      detectedAt: string;
      /** Issuetype */
      issueType: string;
      /** Message */
      message: string;
      /**
       * Severity
       * @default action_required
       * @enum {string}
       */
      severity: 'warning' | 'action_required';
      /** Strategyinstanceid */
      strategyInstanceId?: string | null;
      /** Subjectid */
      subjectId: string;
      /** Subjecttype */
      subjectType: string;
    };
    /** ReconciliationSummaryResponse */
    ReconciliationSummaryResponse: {
      /** Issues */
      issues: components['schemas']['ReconciliationIssueResponse'][];
      /** Manualinterventionbatchcount */
      manualInterventionBatchCount: number;
      /** Resultunknownordercount */
      resultUnknownOrderCount: number;
      /**
       * Status
       * @enum {string}
       */
      status: 'ok' | 'action_required';
    };
    /** RecordCredentialRotationRequest */
    RecordCredentialRotationRequest: {
      /** Credentialref */
      credentialRef: string;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Provider */
      provider: string;
      /** Reason */
      reason: string;
      /**
       * Rotatedat
       * Format: date-time
       */
      rotatedAt: string;
      /** Version */
      version: string;
    };
    /** RiskActionRequest */
    RiskActionRequest: {
      /**
       * Action
       * @enum {string}
       */
      action: 'hold_and_escalate' | 'flatten_filled_legs' | 'cancel_open_legs' | 'substitute_hedge';
      /** Actor */
      actor: string;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Reason */
      reason?: string | null;
      /** Replacementaccountid */
      replacementAccountId?: string | null;
      /** Replacementinstrumentid */
      replacementInstrumentId?: string | null;
      /** Replacementprice */
      replacementPrice?: string | null;
      /** Replacementquantity */
      replacementQuantity?: string | null;
      /** Replacementside */
      replacementSide?: ('buy' | 'sell') | null;
      /** Replacementsymbol */
      replacementSymbol?: string | null;
    };
    /** RiskActionResponse */
    RiskActionResponse: {
      /**
       * Action
       * @enum {string}
       */
      action: 'hold_and_escalate' | 'flatten_filled_legs' | 'cancel_open_legs' | 'substitute_hedge';
      /** Actor */
      actor: string;
      /** Batchid */
      batchId: string;
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Failurereason */
      failureReason?: string | null;
      /** Generatedorderids */
      generatedOrderIds: string[];
      /** Idempotencykey */
      idempotencyKey: string;
      /** Reason */
      reason?: string | null;
      /** Riskactionid */
      riskActionId: string;
      /** Status */
      status: string;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** RuntimeReadinessResponse */
    RuntimeReadinessResponse: {
      /** Backendstatus */
      backendStatus: string;
      /** Databasestatus */
      databaseStatus: string;
      /** Defaulttradingmode */
      defaultTradingMode: string;
      /** Runtimestatus */
      runtimeStatus: string;
    };
    /** StrategyAccountBindingResponse */
    StrategyAccountBindingResponse: {
      /** Accountcode */
      accountCode: string;
      /** Accountid */
      accountId: string;
      /** Bindingid */
      bindingId: string;
      /**
       * Capability
       * @enum {string}
       */
      capability: 'trade_and_read' | 'read_only';
      /** Maxnotional */
      maxNotional: string | null;
      /** Role */
      role: string;
      /** Status */
      status: string;
      /** Strategyinstanceid */
      strategyInstanceId: string;
    };
    /** StrategyAccountSnapshotResponse */
    StrategyAccountSnapshotResponse: {
      /** Accountcode */
      accountCode: string | null;
      /** Accountid */
      accountId: string | null;
      accountRisk: components['schemas']['AccountRiskSnapshotResponse'] | null;
      /** Asof */
      asOf: string | null;
      balance: components['schemas']['BalanceSnapshotResponse'] | null;
      /** Capability */
      capability: ('trade_and_read' | 'read_only') | null;
      /** Coinbalances */
      coinBalances: components['schemas']['CoinBalanceResponse'][];
      /** Dataqualitystate */
      dataQualityState: string;
      /** Economicevents */
      economicEvents: components['schemas']['EconomicEventResponse'][];
      /**
       * Economiceventsquality
       * @default unavailable
       */
      economicEventsQuality: string;
      /** Equityhistory */
      equityHistory: components['schemas']['StrategyEquityHistoryPointResponse'][];
      /** Fills */
      fills: components['schemas']['FillResponse'][];
      /**
       * Fillstotal
       * @default 0
       */
      fillsTotal: number;
      finance: components['schemas']['StrategyPnlResponse'] | null;
      /** Historyend */
      historyEnd: string | null;
      /** Historystart */
      historyStart: string | null;
      /**
       * Isstale
       * @default true
       */
      isStale: boolean;
      /** Lastsuccessfulsyncat */
      lastSuccessfulSyncAt: string | null;
      /** Orders */
      orders: components['schemas']['OrderDetailResponse'][];
      /**
       * Orderstotal
       * @default 0
       */
      ordersTotal: number;
      pnl: components['schemas']['PnlResponse'] | null;
      /** Positions */
      positions: components['schemas']['PositionResponse'][];
      /**
       * Snapshotscope
       * @default strategy
       * @enum {string}
       */
      snapshotScope: 'account' | 'strategy';
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Syncerrorcode */
      syncErrorCode: string | null;
      /** Syncstatus */
      syncStatus: string | null;
    };
    /** StrategyDefinitionResponse */
    StrategyDefinitionResponse: {
      /** Description */
      description: string;
      /** Name */
      name: string;
      /** Status */
      status: string;
      /** Strategyid */
      strategyId: string;
      /** Strategykey */
      strategyKey: string;
      /** V1Scope */
      v1Scope: string;
    };
    /** StrategyEquityHistoryPointResponse */
    StrategyEquityHistoryPointResponse: {
      /**
       * Asof
       * Format: date-time
       */
      asOf: string;
      /**
       * Assetscope
       * @default unspecified
       */
      assetScope: string;
      /** Currency */
      currency?: string | null;
      /** Equity */
      equity: string;
      /** Equitydrawdown */
      equityDrawdown?: string | null;
      /**
       * Equitydrawdownquality
       * @default unavailable
       */
      equityDrawdownQuality: string;
      /** Totalassets */
      totalAssets?: string | null;
      /** Totalassetsdrawdown */
      totalAssetsDrawdown?: string | null;
      /**
       * Totalassetsdrawdownquality
       * @default unavailable
       */
      totalAssetsDrawdownQuality: string;
    };
    /** StrategyInstanceResponse */
    StrategyInstanceResponse: {
      /** Basecurrency */
      baseCurrency: string;
      /** Capitalbase */
      capitalBase: string | null;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Name */
      name: string;
      /** Status */
      status: string;
      /** Strategyid */
      strategyId: string;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Strategykey */
      strategyKey: string;
      /** Strategyname */
      strategyName: string;
      /** Tradingmode */
      tradingMode: string;
      /** Version */
      version: string;
    };
    /**
     * StrategyInstructionAction
     * @enum {string}
     */
    StrategyInstructionAction: 'open' | 'close' | 'risk_disposition';
    /** StrategyManagementOverviewResponse */
    StrategyManagementOverviewResponse: {
      /** Activecapability */
      activeCapability: string;
      /** Bindingcount */
      bindingCount: number;
      /** Category */
      category: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Deskkey */
      deskKey: string;
      executionReadiness?: components['schemas']['StrategyV1ReadinessResponse'] | null;
      /** Instancename */
      instanceName: string;
      /** Latestrunat */
      latestRunAt?: string | null;
      /** Latestrunstatus */
      latestRunStatus?: string | null;
      /** Operatingstatus */
      operatingStatus: string;
      /** Primaryaccountcode */
      primaryAccountCode?: string | null;
      /** Primaryaccountdataqualitystate */
      primaryAccountDataQualityState?: string | null;
      /** Primaryaccountstatus */
      primaryAccountStatus?: string | null;
      /** Sortorder */
      sortOrder: number;
      /** Strategyid */
      strategyId: string;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Strategykey */
      strategyKey: string;
      /** Strategyname */
      strategyName: string;
      /** Tradingmode */
      tradingMode: string;
      /** V1Scope */
      v1Scope: string;
    };
    /** StrategyNavSnapshotResponse */
    StrategyNavSnapshotResponse: {
      /** Capitalbase */
      capitalBase: string;
      /** Currency */
      currency: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Equity */
      equity: string;
      /** Nav */
      nav: string;
      /** Snapshotid */
      snapshotId: string;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /**
       * Valuationtime
       * Format: date-time
       */
      valuationTime: string;
    };
    /** StrategyPnlResponse */
    StrategyPnlResponse: {
      /** Byaccount */
      byAccount: components['schemas']['FinancialAmountsResponse'][];
      /** Bycurrency */
      byCurrency: components['schemas']['FinancialAmountsResponse'][];
      /** Coverage */
      coverage: components['schemas']['FinancialCoverageResponse'][];
      /** Currency */
      currency: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Economicevents */
      economicEvents: components['schemas']['EconomicEventResponse'][];
      /** Fees */
      fees: string | null;
      /** Fundingpnl */
      fundingPnl: string | null;
      /** Issues */
      issues: string[];
      /** Netpnl */
      netPnl: string | null;
      /** Positions */
      positions: {
        [key: string]: unknown;
      }[];
      /** Realizedpnl */
      realizedPnl: string | null;
      /**
       * Scope
       * @default strategy
       */
      scope: string;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Swappnl */
      swapPnl: string | null;
      /** Timeline */
      timeline: components['schemas']['FinancialTimelinePointResponse'][];
      /** Tradingpnl */
      tradingPnl: string | null;
      /** Unattributedevents */
      unattributedEvents: components['schemas']['EconomicEventResponse'][];
    };
    /** StrategyRunResponse */
    StrategyRunResponse: {
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Direction */
      direction: string;
      executionBatch?: components['schemas']['ExecutionBatchResponse'] | null;
      /** Executionbatchid */
      executionBatchId?: string | null;
      /** Failurereason */
      failureReason?: string | null;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Reason */
      reason?: string | null;
      /**
       * Status
       * @enum {string}
       */
      status: 'pending' | 'executing' | 'completed' | 'failed' | 'manual_intervention';
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Strategykey */
      strategyKey: string;
      /** Strategyrunid */
      strategyRunId: string;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** StrategyV1ReadinessResponse */
    StrategyV1ReadinessResponse: {
      /** Blockers */
      blockers: string[];
      /** Latestrunstatus */
      latestRunStatus?: string | null;
      /** Manualinterventioncount */
      manualInterventionCount: number;
      /** Resultunknownordercount */
      resultUnknownOrderCount: number;
      /** Runnable */
      runnable: boolean;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Strategykey */
      strategyKey: string;
      /** Warnings */
      warnings: string[];
    };
    /** TradeCommandResponse */
    TradeCommandResponse: {
      /** Accountid */
      accountId: string;
      /**
       * Createdat
       * Format: date-time
       */
      createdAt: string;
      /** Idempotencykey */
      idempotencyKey: string;
      /** Instrumentid */
      instrumentId: string;
      /** Platformorderid */
      platformOrderId: string | null;
      /** Status */
      status: string;
      /** Strategyinstanceid */
      strategyInstanceId: string;
      /** Tradecommandid */
      tradeCommandId: string;
      /**
       * Updatedat
       * Format: date-time
       */
      updatedAt: string;
    };
    /** TradingSafetyResponse */
    TradingSafetyResponse: {
      /** Defaulttradingenvironment */
      defaultTradingEnvironment: string;
      /** Founderdemolocalselfapprovalenabled */
      founderDemoLocalSelfApprovalEnabled: boolean;
      /** Liveguardpolicy */
      liveGuardPolicy: string;
      /** Livetradingenabled */
      liveTradingEnabled: boolean;
      /** Secretstoragepolicy */
      secretStoragePolicy: string;
    };
    /** ValidationError */
    ValidationError: {
      /** Context */
      ctx?: Record<string, never>;
      /** Input */
      input?: unknown;
      /** Location */
      loc: (string | number)[];
      /** Message */
      msg: string;
      /** Error Type */
      type: string;
    };
    /** VenueAccountRiskSnapshotResponse */
    VenueAccountRiskSnapshotResponse: {
      /** Accountid */
      accountId: string;
      /** Accountimrate */
      accountImRate?: string | null;
      /** Accountmmrate */
      accountMmRate?: string | null;
      /** Asof */
      asOf: string;
      /** Availablebalance */
      availableBalance?: string | null;
      /** Currency */
      currency: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Equity */
      equity?: string | null;
      /** Experttradingallowed */
      expertTradingAllowed?: boolean | null;
      /** Fieldavailability */
      fieldAvailability?: {
        [key: string]: string;
      } | null;
      /** Initialmargin */
      initialMargin?: string | null;
      /** Leverage */
      leverage?: string | null;
      /** Maintenancemargin */
      maintenanceMargin?: string | null;
      /** Marginbalance */
      marginBalance?: string | null;
      /** Margincalllevel */
      marginCallLevel?: string | null;
      /** Marginlevel */
      marginLevel?: string | null;
      /** Marginmode */
      marginMode?: string | null;
      /** Marginthresholdmode */
      marginThresholdMode?: string | null;
      /** Source */
      source: string;
      /** Stopoutlevel */
      stopOutLevel?: string | null;
      /** Tradeallowed */
      tradeAllowed?: boolean | null;
      /** Unrealizedpnl */
      unrealizedPnl?: string | null;
      /** Walletbalance */
      walletBalance?: string | null;
    } & {
      [key: string]: unknown;
    };
    /** VenueFillSnapshotResponse */
    VenueFillSnapshotResponse: {
      /** Accountid */
      accountId: string;
      /** Currency */
      currency: string;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Externalfillid */
      externalFillId: string;
      /** Externalorderid */
      externalOrderId: string;
      /** Fee */
      fee: string | null;
      /** Occurredat */
      occurredAt: string;
      /** Price */
      price: string;
      /** Quantity */
      quantity: string;
      /** Side */
      side: 'buy' | 'sell';
      /** Source */
      source: string;
      /** Symbol */
      symbol: string;
    } & {
      [key: string]: unknown;
    };
    /** VenueOrderSnapshotResponse */
    VenueOrderSnapshotResponse: {
      /** Accountid */
      accountId: string;
      /** Asof */
      asOf: string;
      /** Averagefillprice */
      averageFillPrice?: string | null;
      /** Cancelreason */
      cancelReason?: string | null;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Externalorderid */
      externalOrderId: string;
      /** Filledquantity */
      filledQuantity: string;
      /** Ordertype */
      orderType: 'market' | 'limit';
      /** Platformorderid */
      platformOrderId: string;
      /** Positionid */
      positionId?: string | null;
      /** Positionindex */
      positionIndex?: number | null;
      /** Price */
      price?: string | null;
      /** Quantity */
      quantity: string;
      /** Reduceonly */
      reduceOnly?: boolean | null;
      /** Rejectreason */
      rejectReason?: string | null;
      /** Remainingquantity */
      remainingQuantity: string;
      /** Side */
      side: 'buy' | 'sell';
      /** Source */
      source: string;
      /** Status */
      status: string;
      /** Symbol */
      symbol: string;
      /** Timeinforce */
      timeInForce?: string | null;
    } & {
      [key: string]: unknown;
    };
    /** VenuePositionResponse */
    VenuePositionResponse: {
      /** Accountid */
      accountId?: string | null;
      /** Asof */
      asOf?: string | null;
      /** Averageprice */
      averagePrice?: string | null;
      /** Currency */
      currency?: string | null;
      /** Externalid */
      externalId?: string | null;
      /** Quantity */
      quantity: string;
      /** Side */
      side: string;
      /** Symbol */
      symbol: string;
      /** Unrealizedpnl */
      unrealizedPnl?: string | null;
    };
    /** VenuePositionSnapshotResponse */
    VenuePositionSnapshotResponse: {
      /** Accountid */
      accountId: string;
      /** Asof */
      asOf: string;
      /** Averageprice */
      averagePrice?: string | null;
      /** Breakevenprice */
      breakEvenPrice?: string | null;
      /** Currency */
      currency: string;
      /** Currentprice */
      currentPrice?: string | null;
      /** Dataqualitystate */
      dataQualityState: string;
      /** Externalpositionid */
      externalPositionId: string;
      /** Fieldavailability */
      fieldAvailability?: {
        [key: string]: string;
      } | null;
      /** Initialmargin */
      initialMargin?: string | null;
      /** Instrumentid */
      instrumentId: string;
      /** Leverage */
      leverage?: string | null;
      /** Liquidationprice */
      liquidationPrice?: string | null;
      /** Liquidationpricesource */
      liquidationPriceSource: string;
      /** Maintenancemargin */
      maintenanceMargin?: string | null;
      /** Markprice */
      markPrice?: string | null;
      /** Netquantity */
      netQuantity: string;
      /** Opentime */
      openTime?: string | null;
      /** Positionstatus */
      positionStatus?: string | null;
      /** Positionvalue */
      positionValue?: string | null;
      /** Realizedpnl */
      realizedPnl?: string | null;
      /** Source */
      source: string;
      /** Stoplossprice */
      stopLossPrice?: string | null;
      /** Swap */
      swap?: string | null;
      /** Symbol */
      symbol: string;
      /** Takeprofitprice */
      takeProfitPrice?: string | null;
      /** Unrealizedpnl */
      unrealizedPnl?: string | null;
    } & {
      [key: string]: unknown;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
  accounts_api_v1_accounts_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['AccountResponse'][];
        };
      };
    };
  };
  account_api_v1_accounts__account_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        account_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['AccountResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  latest_balance_api_v1_accounts__account_id__balances_latest_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        account_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['BalanceSnapshotResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  equity_history_api_v1_accounts__account_id__equity_history_get: {
    parameters: {
      query?: {
        currency?: string | null;
      };
      header?: never;
      path: {
        account_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['EquityHistoryPoint'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  get_pnl_api_v1_accounts__account_id__pnl__instrument_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        account_id: string;
        instrument_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['PnlResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  account_positions_api_v1_accounts__account_id__positions_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        account_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['PositionResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  get_position_api_v1_accounts__account_id__positions__instrument_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        account_id: string;
        instrument_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['PositionResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  instruments_api_v1_instruments_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InstrumentResponse'][];
        };
      };
    };
  };
  instrument_api_v1_instruments__instrument_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        instrument_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InstrumentResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  get_live_sessions_api_v1_live_trading_sessions_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['LiveTradingSessionResponse'][];
        };
      };
    };
  };
  create_live_session_api_v1_live_trading_sessions_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['LiveTradingSessionRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['LiveTradingSessionResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  approve_session_api_v1_live_trading_sessions__session_id__approve_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['LiveTradingSessionApprovalRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['LiveTradingSessionResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  revoke_session_api_v1_live_trading_sessions__session_id__revoke_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        session_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['LiveTradingSessionRevocationRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['LiveTradingSessionResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  reconciliation_summary_api_v1_ops_reconciliation_summary_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ReconciliationSummaryResponse'];
        };
      };
    };
  };
  credential_references_api_v1_security_credential_references_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CredentialReferenceResponse'][];
        };
      };
    };
  };
  credential_rotations_api_v1_security_credential_rotations_get: {
    parameters: {
      query?: {
        credential_ref?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CredentialRotationResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  create_credential_rotation_api_v1_security_credential_rotations_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['RecordCredentialRotationRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CredentialRotationResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  exchange_connectivity_api_v1_security_exchange_connectivity_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExchangeConnectivityResponse'];
        };
      };
    };
  };
  exchange_venue_readiness_api_v1_security_exchange_venue_readiness_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExchangeVenueReadinessResponse'];
        };
      };
    };
  };
  trading_safety_api_v1_security_trading_safety_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['TradingSafetyResponse'];
        };
      };
    };
  };
  strategies_definitions_api_v1_strategies_definitions_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyDefinitionResponse'][];
        };
      };
    };
  };
  strategies_instances_api_v1_strategies_instances_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyInstanceResponse'][];
        };
      };
    };
  };
  strategy_instance_api_v1_strategies_instances__strategy_instance_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyInstanceResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  strategy_account_snapshot_api_v1_strategies_instances__strategy_instance_id__account_snapshot_get: {
    parameters: {
      query?: {
        accountId?: string | null;
      };
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyAccountSnapshotResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  strategy_accounts_api_v1_strategies_instances__strategy_instance_id__accounts_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyAccountBindingResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  read_execution_risk_policy_api_v1_strategies_instances__strategy_instance_id__execution_risk_policy_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExecutionRiskPolicyResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  change_execution_risk_policy_api_v1_strategies_instances__strategy_instance_id__execution_risk_policy_put: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['ExecutionRiskPolicyUpdateRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExecutionRiskPolicyResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  rebuild_financials_api_v1_strategies_instances__strategy_instance_id__financials_rebuild_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FinancialProjectionRebuildResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  get_formal_nav_snapshots_api_v1_strategies_instances__strategy_instance_id__formal_nav_snapshots_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FormalNavSnapshotResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  run_formal_nav_api_v1_strategies_instances__strategy_instance_id__formal_nav_snapshots_run_post: {
    parameters: {
      query?: {
        valuationTime?: string | null;
      };
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FormalNavSnapshotResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  get_formal_pnl_api_v1_strategies_instances__strategy_instance_id__formal_pnl_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FormalPnlResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  get_formal_positions_api_v1_strategies_instances__strategy_instance_id__formal_positions_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FormalPositionResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  strategy_nav_snapshots_api_v1_strategies_instances__strategy_instance_id__nav_snapshots_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyNavSnapshotResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  run_strategy_nav_snapshot_api_v1_strategies_instances__strategy_instance_id__nav_snapshots_run_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyNavSnapshotResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  strategy_pnl_api_v1_strategies_instances__strategy_instance_id__pnl_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyPnlResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  strategy_runs_api_v1_strategies_instances__strategy_instance_id__runs_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyRunResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  create_run_api_v1_strategies_instances__strategy_instance_id__runs_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateStrategyRunRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyRunResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  strategy_v1_readiness_api_v1_strategies_instances__strategy_instance_id__v1_readiness_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyV1ReadinessResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  strategy_management_overview_api_v1_strategies_management_overview_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['StrategyManagementOverviewResponse'][];
        };
      };
    };
  };
  strategy_instructions_api_v1_strategies__strategy_instance_id__instructions_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': {
            [key: string]: unknown;
          }[];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  create_strategy_instruction_api_v1_strategies__strategy_instance_id__instructions_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        strategy_instance_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateStrategyInstructionRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': {
            [key: string]: unknown;
          };
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  runtime_readiness_api_v1_system_runtime_readiness_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['RuntimeReadinessResponse'];
        };
      };
    };
  };
  create_command_api_v1_trading_commands_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateTradeCommandRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['TradeCommandResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  trade_command_api_v1_trading_commands__trade_command_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        trade_command_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['TradeCommandResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  exit_plans_api_v1_trading_cross_spread_exit_plans_get: {
    parameters: {
      query?: {
        status?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadExitPlanResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  evaluate_market_exit_plans_api_v1_trading_cross_spread_exit_plans_evaluate_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadExitEvaluationResponse'];
        };
      };
    };
  };
  update_exit_plan_api_v1_trading_cross_spread_exit_plans__plan_id__patch: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        plan_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CrossSpreadExitPlanUpdateRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadExitPlanResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  close_market_lifecycle_api_v1_trading_cross_spread_exit_plans__plan_id__close_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        plan_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CrossSpreadMarketCloseRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadCloseResult'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cross_spread_funding_transfer_api_v1_trading_cross_spread_funding_transfer_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateInternalCapitalTransferRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InternalCapitalTransferResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cross_spread_funding_transfer_quote_api_v1_trading_cross_spread_funding_transfer_quote_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FundingTransferQuoteResponse'];
        };
      };
    };
  };
  cross_spread_funding_transfer_status_api_v1_trading_cross_spread_funding_transfers__transfer_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        transfer_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InternalCapitalTransferResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cross_spread_funding_transfer_cancel_api_v1_trading_cross_spread_funding_transfers__transfer_id__cancel_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        transfer_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['InternalCapitalTransferResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cross_spread_history_api_v1_trading_cross_spread_history_get: {
    parameters: {
      query?: {
        limit?: number;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadHistoryPointResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cross_spread_leverage_api_v1_trading_cross_spread_leverage_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadLeverageResponse'];
        };
      };
    };
  };
  set_cross_spread_leverage_api_v1_trading_cross_spread_leverage_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CrossSpreadLeverageRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadLeverageResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  open_market_lifecycle_api_v1_trading_cross_spread_lifecycle_open_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CrossSpreadMarketOpenRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadOpenResult'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cross_spread_market_command_api_v1_trading_cross_spread_market_command_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CrossSpreadMarketCommandRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExecutionBatchResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cross_spread_observability_api_v1_trading_cross_spread_observability_get: {
    parameters: {
      query?: {
        historyHours?: number;
        limit?: number;
        mode?: 'fast' | 'audit';
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadObservabilityResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cross_spread_preflight_api_v1_trading_cross_spread_preflight_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CrossSpreadPreflightRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadPreflightResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cross_spread_snapshot_api_v1_trading_cross_spread_snapshot_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['CrossSpreadSnapshotResponse'];
        };
      };
    };
  };
  execution_batches_api_v1_trading_execution_batches_get: {
    parameters: {
      query?: {
        strategyInstanceId?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExecutionBatchResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  create_batch_api_v1_trading_execution_batches_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateExecutionBatchRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExecutionBatchResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  get_batch_api_v1_trading_execution_batches__batch_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExecutionBatchResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  read_batch_risk_api_v1_trading_execution_batches__batch_id__risk_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['BatchRiskResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  read_risk_actions_api_v1_trading_execution_batches__batch_id__risk_actions_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['RiskActionResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  create_risk_action_api_v1_trading_execution_batches__batch_id__risk_actions_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        batch_id: string;
      };
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['RiskActionRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['RiskActionResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  fills_api_v1_trading_fills_get: {
    parameters: {
      query?: {
        strategyInstanceId?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FillResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  funding_execution_context_api_v1_trading_funding_execution_context_get: {
    parameters: {
      query?: {
        perpetualSymbol?: string | null;
        spotSymbol?: string | null;
        notional?: number | string | null;
        quantity?: number | string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FundingExecutionContextResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  funding_instruction_by_idempotency_api_v1_trading_funding_instructions_get: {
    parameters: {
      query: {
        idempotencyKey: string;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FundingWorkspaceResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  funding_instruction_submit_api_v1_trading_funding_instructions_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['FundingInstructionRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FundingWorkspaceResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  funding_instruction_workspace_api_v1_trading_funding_instructions__instruction_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        instruction_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FundingWorkspaceResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  funding_market_command_api_v1_trading_funding_market_command_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['FundingMarketCommandRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExecutionBatchResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  funding_positions_api_v1_trading_funding_positions_get: {
    parameters: {
      query?: {
        scope?: string;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['FundingPositionGroupResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  orders_api_v1_trading_orders_get: {
    parameters: {
      query?: {
        strategyInstanceId?: string | null;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['OrderDetailResponse'][];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  create_order_api_v1_trading_orders_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['CreateOrderRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['OrderResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  order_api_v1_trading_orders__order_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        order_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['OrderDetailResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  reconcile_trading_order_api_v1_trading_orders__order_id__reconcile_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        order_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['OrderResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  resolve_missing_external_platform_order_api_v1_trading_orders__order_id__resolve_missing_external_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        order_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['OrderVenueReconciliationResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  reconcile_platform_order_api_v1_trading_orders__order_id__venue_reconcile_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        order_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['OrderVenueReconciliationResponse'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
}
