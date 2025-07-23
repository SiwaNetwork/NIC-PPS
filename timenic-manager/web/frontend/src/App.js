import React, { useState, useEffect, useRef } from 'react';
import { 
  Layout, Menu, Card, Button, Space, Tag, Statistic, Row, Col, 
  Alert, message, Modal, Form, Input, InputNumber, Select, Spin,
  Tabs, Table, Progress, Badge, Divider, Typography, Switch
} from 'antd';
import {
  DashboardOutlined, ControlOutlined, SyncOutlined, 
  SettingOutlined, ApiOutlined, CheckCircleOutlined,
  CloseCircleOutlined, ClockCircleOutlined, ThunderboltOutlined,
  ExportOutlined, ImportOutlined, ReloadOutlined
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import dayjs from 'dayjs';
import axios from 'axios';
import './App.css';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;
const { TabPane } = Tabs;

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKey, setSelectedKey] = useState('dashboard');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);
  const [syncData, setSyncData] = useState([]);
  const [ppsEvents, setPpsEvents] = useState([]);
  const wsRef = useRef(null);

  // WebSocket connection
  useEffect(() => {
    connectWebSocket();
    fetchStatus();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    const ws = new WebSocket(`ws://localhost:8000/ws`);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'status') {
        setStatus(data.data);
      } else if (data.type === 'sync_status') {
        if (data.data) {
          setSyncStatus(data.data);
          setSyncData(prev => {
            const newData = [...prev, {
              time: dayjs(data.data.timestamp * 1000).format('HH:mm:ss'),
              offset: data.data.offset_ns,
              frequency: data.data.frequency_ppb,
              rms: data.data.rms_ns
            }];
            return newData.slice(-50); // Keep last 50 points
          });
        } else {
          setSyncStatus(null);
        }
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      message.error('WebSocket connection error');
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setTimeout(connectWebSocket, 5000); // Reconnect after 5 seconds
    };
    
    wsRef.current = ws;
  };

  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/status`);
      setStatus(response.data);
    } catch (error) {
      message.error('Failed to fetch status');
    }
  };

  const handleEnablePPSOutput = async () => {
    Modal.confirm({
      title: 'Enable PPS Output',
      content: (
        <Form layout="vertical" id="pps-output-form">
          <Form.Item label="Frequency (Hz)" name="frequency" initialValue={1}>
            <InputNumber min={1} max={1000000} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      ),
      onOk: async () => {
        const form = document.getElementById('pps-output-form');
        const frequency = form.querySelector('input').value;
        
        setLoading(true);
        try {
          const response = await axios.post(`${API_BASE}/api/pps/output/enable`, {
            frequency: parseInt(frequency)
          });
          
          if (response.data.success) {
            message.success(response.data.message);
            fetchStatus();
          } else {
            message.error(response.data.message);
          }
        } catch (error) {
          message.error('Failed to enable PPS output');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  const handleEnablePPSInput = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/api/pps/input/enable`);
      
      if (response.data.success) {
        message.success(response.data.message);
        fetchStatus();
      } else {
        message.error(response.data.message);
      }
    } catch (error) {
      message.error('Failed to enable PPS input');
    } finally {
      setLoading(false);
    }
  };

  const handleReadPPSEvents = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/api/pps/events?count=10`);
      
      if (response.data.success) {
        setPpsEvents(response.data.events);
        Modal.info({
          title: 'PPS Events',
          width: 600,
          content: (
            <Table
              dataSource={response.data.events}
              columns={[
                { title: 'Event #', dataIndex: 'index', key: 'index' },
                { title: 'Timestamp', dataIndex: 'timestamp', key: 'timestamp',
                  render: (ts) => ts.toFixed(9) },
                { title: 'Time', dataIndex: 'time', key: 'time' }
              ]}
              size="small"
              pagination={false}
            />
          )
        });
      }
    } catch (error) {
      message.error('Failed to read PPS events');
    } finally {
      setLoading(false);
    }
  };

  const handleStartSync = async () => {
    Modal.confirm({
      title: 'Start Synchronization',
      content: (
        <Form layout="vertical" id="sync-form">
          <Form.Item label="Pin Index" name="pin_index" initialValue={1}>
            <InputNumber min={0} max={3} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      ),
      onOk: async () => {
        const form = document.getElementById('sync-form');
        const pinIndex = form.querySelector('input').value;
        
        setLoading(true);
        try {
          const response = await axios.post(`${API_BASE}/api/sync/start`, {
            pin_index: parseInt(pinIndex)
          });
          
          if (response.data.success) {
            message.success(response.data.message);
            setSyncData([]); // Clear previous data
          } else {
            message.error(response.data.message);
          }
        } catch (error) {
          message.error('Failed to start synchronization');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  const handleStopSync = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/api/sync/stop`);
      
      if (response.data.success) {
        message.success(response.data.message);
        setSyncStatus(null);
      } else {
        message.error(response.data.message);
      }
    } catch (error) {
      message.error('Failed to stop synchronization');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSetup = async () => {
    Modal.confirm({
      title: 'Quick Setup',
      content: 'This will configure basic TimeNIC settings. Continue?',
      onOk: async () => {
        setLoading(true);
        try {
          const response = await axios.post(`${API_BASE}/api/quick-setup`);
          
          if (response.data.success) {
            message.success(response.data.message);
            
            // Show results
            Modal.success({
              title: 'Quick Setup Completed',
              content: (
                <div>
                  {response.data.data.steps.map((step, index) => (
                    <div key={index}>
                      <CheckCircleOutlined style={{ color: '#52c41a' }} /> {step}
                    </div>
                  ))}
                </div>
              )
            });
            
            fetchStatus();
          } else {
            message.error(response.data.message);
          }
        } catch (error) {
          message.error('Quick setup failed');
        } finally {
          setLoading(false);
        }
      }
    });
  };

  const renderDashboard = () => (
    <div>
      <Title level={2}>TimeNIC Dashboard</Title>
      
      {/* Status Cards */}
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Device Status"
              value={status?.device ? 'Connected' : 'Disconnected'}
              valueStyle={{ color: status?.device ? '#3f8600' : '#cf1322' }}
              prefix={status?.device ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="PPS Output"
              value={status?.pps_output?.enabled ? 'Enabled' : 'Disabled'}
              valueStyle={{ color: status?.pps_output?.enabled ? '#3f8600' : '#999' }}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="PPS Input"
              value={status?.pps_input?.enabled ? 'Enabled' : 'Disabled'}
              valueStyle={{ color: status?.pps_input?.enabled ? '#3f8600' : '#999' }}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="PTM Status"
              value={status?.ptm_status || 'Unknown'}
              valueStyle={{ 
                color: status?.ptm_status === 'ENABLED' ? '#3f8600' : 
                       status?.ptm_status === 'DISABLED' ? '#faad14' : '#999' 
              }}
            />
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* Device Information */}
      {status?.device && (
        <Card title="Device Information" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Text strong>Interface:</Text> {status.device.interface}
            </Col>
            <Col span={12}>
              <Text strong>PTP Device:</Text> {status.device.ptp_device}
            </Col>
            <Col span={12}>
              <Text strong>Clock Index:</Text> {status.device.clock_index}
            </Col>
            <Col span={12}>
              <Text strong>Capabilities:</Text> {status.device.capabilities?.join(', ')}
            </Col>
          </Row>
        </Card>
      )}

      {/* PHC Time */}
      {status?.phc_time && (
        <Card title="PHC Time" style={{ marginTop: 16 }}>
          <Statistic
            value={dayjs(status.phc_time * 1000).format('HH:mm:ss.SSS')}
            prefix={<ClockCircleOutlined />}
          />
        </Card>
      )}

      {/* Quick Actions */}
      <Card title="Quick Actions" style={{ marginTop: 16 }}>
        <Space>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleQuickSetup}>
            Quick Setup
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchStatus}>
            Refresh Status
          </Button>
        </Space>
      </Card>
    </div>
  );

  const renderControl = () => (
    <div>
      <Title level={2}>Device Control</Title>
      
      <Row gutter={16}>
        <Col span={12}>
          <Card title="PPS Output Control (SMA1)">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="Current Status"
                description={status?.pps_output?.enabled ? "PPS output is enabled" : "PPS output is disabled"}
                type={status?.pps_output?.enabled ? "success" : "info"}
                showIcon
              />
              <Button 
                type="primary" 
                icon={<ThunderboltOutlined />}
                onClick={handleEnablePPSOutput}
                loading={loading}
                block
              >
                Enable PPS Output
              </Button>
            </Space>
          </Card>
        </Col>
        
        <Col span={12}>
          <Card title="PPS Input Control (SMA2)">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="Current Status"
                description={status?.pps_input?.enabled ? "PPS input is enabled" : "PPS input is disabled"}
                type={status?.pps_input?.enabled ? "success" : "info"}
                showIcon
              />
              <Button 
                type="primary" 
                icon={<ApiOutlined />}
                onClick={handleEnablePPSInput}
                loading={loading}
                block
              >
                Enable PPS Input
              </Button>
              <Button 
                icon={<ClockCircleOutlined />}
                onClick={handleReadPPSEvents}
                loading={loading}
                block
              >
                Read PPS Events
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card title="PTM Control" style={{ marginTop: 16 }}>
        <Alert
          message="PTM Status"
          description={`Current status: ${status?.ptm_status || 'Unknown'}`}
          type={
            status?.ptm_status === 'ENABLED' ? 'success' : 
            status?.ptm_status === 'DISABLED' ? 'warning' : 'info'
          }
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form layout="vertical">
          <Form.Item label="PCI Address">
            <Input placeholder="e.g., 0000:03:00.0" />
          </Form.Item>
          <Button type="primary" icon={<SettingOutlined />}>
            Enable PTM
          </Button>
        </Form>
      </Card>
    </div>
  );

  const renderSync = () => (
    <div>
      <Title level={2}>Synchronization</Title>
      
      <Card title="Synchronization Control">
        <Space>
          {!syncStatus ? (
            <Button 
              type="primary" 
              icon={<SyncOutlined />}
              onClick={handleStartSync}
              loading={loading}
            >
              Start Synchronization
            </Button>
          ) : (
            <Button 
              type="danger" 
              icon={<CloseCircleOutlined />}
              onClick={handleStopSync}
              loading={loading}
            >
              Stop Synchronization
            </Button>
          )}
        </Space>
      </Card>

      {syncStatus && (
        <>
          <Card title="Synchronization Status" style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="Status"
                  value={syncStatus.is_synced ? 'SYNCED' : 'SYNCING'}
                  valueStyle={{ color: syncStatus.is_synced ? '#3f8600' : '#faad14' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Offset"
                  value={syncStatus.offset_ns?.toFixed(1)}
                  suffix="ns"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="Frequency"
                  value={syncStatus.frequency_ppb?.toFixed(1)}
                  suffix="ppb"
                  prefix={syncStatus.frequency_ppb > 0 ? '+' : ''}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="RMS"
                  value={syncStatus.rms_ns?.toFixed(1)}
                  suffix="ns"
                />
              </Col>
            </Row>
          </Card>

          <Card title="Synchronization Graph" style={{ marginTop: 16 }}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={syncData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis yAxisId="left" label={{ value: 'Offset (ns)', angle: -90, position: 'insideLeft' }} />
                <YAxis yAxisId="right" orientation="right" label={{ value: 'Frequency (ppb)', angle: 90, position: 'insideRight' }} />
                <Tooltip />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="offset" stroke="#8884d8" name="Offset (ns)" />
                <Line yAxisId="right" type="monotone" dataKey="frequency" stroke="#82ca9d" name="Frequency (ppb)" />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </>
      )}
    </div>
  );

  const renderConfiguration = () => (
    <div>
      <Title level={2}>Configuration</Title>
      
      <Card title="Device Configuration">
        <Form layout="vertical">
          <Form.Item label="Network Interface">
            <Input defaultValue={status?.device?.interface || 'enp3s0'} />
          </Form.Item>
          <Form.Item label="PTP Device">
            <Input defaultValue={status?.device?.ptp_device || '/dev/ptp0'} />
          </Form.Item>
          <Button type="primary" icon={<SettingOutlined />}>
            Apply Configuration
          </Button>
        </Form>
      </Card>

      <Card title="Driver Management" style={{ marginTop: 16 }}>
        <Alert
          message="Driver Installation"
          description="Installing the patched driver requires root privileges and system reboot"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Button type="primary" danger icon={<SettingOutlined />}>
          Install Patched Driver
        </Button>
      </Card>

      <Card title="Configuration Export/Import" style={{ marginTop: 16 }}>
        <Space>
          <Button icon={<ExportOutlined />}>
            Export Configuration
          </Button>
          <Button icon={<ImportOutlined />}>
            Import Configuration
          </Button>
        </Space>
      </Card>
    </div>
  );

  const renderContent = () => {
    switch (selectedKey) {
      case 'dashboard':
        return renderDashboard();
      case 'control':
        return renderControl();
      case 'sync':
        return renderSync();
      case 'config':
        return renderConfiguration();
      default:
        return renderDashboard();
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div className="logo" style={{ height: 32, margin: 16, background: 'rgba(255, 255, 255, 0.3)' }} />
        <Menu
          theme="dark"
          selectedKeys={[selectedKey]}
          mode="inline"
          onClick={({ key }) => setSelectedKey(key)}
        >
          <Menu.Item key="dashboard" icon={<DashboardOutlined />}>
            Dashboard
          </Menu.Item>
          <Menu.Item key="control" icon={<ControlOutlined />}>
            Control
          </Menu.Item>
          <Menu.Item key="sync" icon={<SyncOutlined />}>
            Synchronization
          </Menu.Item>
          <Menu.Item key="config" icon={<SettingOutlined />}>
            Configuration
          </Menu.Item>
        </Menu>
      </Sider>
      <Layout>
        <Header style={{ padding: 0, background: '#fff' }}>
          <Title level={3} style={{ margin: '16px 24px' }}>TimeNIC Manager</Title>
        </Header>
        <Content style={{ margin: '24px 16px' }}>
          <div style={{ padding: 24, minHeight: 360, background: '#fff' }}>
            <Spin spinning={loading}>
              {renderContent()}
            </Spin>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;