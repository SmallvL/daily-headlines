import {
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
  TeamOutlined,
  UserAddOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import { useState } from "react";

import { AuthSession } from "../../shared/api/auth";
import {
  UserGroup,
  addGroupMembers,
  createGroup,
  deleteGroup,
  getGroup,
  listGroups,
  listAdminUsers,
  removeGroupMember,
} from "../../shared/api/admin";

type GroupsPageProps = { session: AuthSession };

export function GroupsPage({ session }: GroupsPageProps) {
  const [createOpen, setCreateOpen] = useState(false);
  const [detailGroupId, setDetailGroupId] = useState<string | null>(null);
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();
  const [form] = Form.useForm();
  const [addForm] = Form.useForm();

  const groupsQuery = useQuery({
    queryKey: ["admin-groups"],
    queryFn: () => listGroups(session),
  });

  const detailQuery = useQuery({
    queryKey: ["admin-group-detail", detailGroupId],
    queryFn: () => getGroup(session, detailGroupId!),
    enabled: !!detailGroupId,
  });

  const usersQuery = useQuery({
    queryKey: ["admin-users-for-member"],
    queryFn: () => listAdminUsers(session),
  });

  async function handleCreate() {
    try {
      const values = await form.validateFields();
      await createGroup(session, values);
      messageApi.success("组已创建");
      setCreateOpen(false);
      form.resetFields();
      groupsQuery.refetch();
    } catch (e) {
      if (typeof e === "object" && e !== null && "errorFields" in e) return; // validation
      messageApi.error(e instanceof Error ? e.message : "创建失败");
    }
  }

  async function handleDelete(groupId: string) {
    try {
      await deleteGroup(session, groupId);
      messageApi.success("组已删除");
      groupsQuery.refetch();
      if (detailGroupId === groupId) setDetailGroupId(null);
    } catch {
      messageApi.error("删除失败");
    }
  }

  async function handleAddMembers() {
    try {
      const values = await addForm.validateFields();
      await addGroupMembers(session, detailGroupId!, values.user_ids);
      messageApi.success("成员已添加");
      setAddMemberOpen(false);
      addForm.resetFields();
      detailQuery.refetch();
      groupsQuery.refetch();
    } catch (e) {
      if (typeof e === "object" && e !== null && "errorFields" in e) return; // validation
      messageApi.error(e instanceof Error ? e.message : "添加成员失败");
    }
  }

  async function handleRemoveMember(userId: string) {
    try {
      await removeGroupMember(session, detailGroupId!, userId);
      messageApi.success("成员已移除");
      detailQuery.refetch();
      groupsQuery.refetch();
    } catch {
      messageApi.error("移除失败");
    }
  }

  const memberUserIds = new Set(
    (detailQuery.data?.members ?? []).map((m) => m.user_id)
  );
  const availableUsers = (usersQuery.data?.items ?? []).filter(
    (u) => !memberUserIds.has(u.id)
  );

  return (
    <div className="groups-page">
      {contextHolder}
      <Typography.Title level={4}>组管理</Typography.Title>
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateOpen(true)}
        >
          创建组
        </Button>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => groupsQuery.refetch()}
        >
          刷新
        </Button>
      </Space>

      <List
        loading={groupsQuery.isLoading}
        dataSource={groupsQuery.data ?? []}
        renderItem={(group: UserGroup) => (
          <List.Item
            actions={[
              <Button
                key="detail"
                size="small"
                icon={<TeamOutlined />}
                onClick={() => setDetailGroupId(group.id)}
              >
                成员
              </Button>,
              <Popconfirm
                key="delete"
                title="确定删除此组？"
                onConfirm={() => handleDelete(group.id)}
              >
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>,
            ]}
          >
            <List.Item.Meta
              title={group.name}
              description={
                <Space>
                  <span>{group.description || "无描述"}</span>
                  <Tag>{group.member_count} 人</Tag>
                </Space>
              }
            />
          </List.Item>
        )}
      />

      {/* Create Group Modal */}
      <Modal
        title="创建组"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => {
          setCreateOpen(false);
          form.resetFields();
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="组名"
            rules={[{ required: true, message: "请输入组名" }]}
          >
            <Input placeholder="例如：产品团队" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="可选描述" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Group Detail Modal */}
      <Modal
        title={`组成员 — ${detailQuery.data?.name ?? ""}`}
        open={!!detailGroupId}
        onCancel={() => setDetailGroupId(null)}
        footer={
          <Button
            type="primary"
            icon={<UserAddOutlined />}
            onClick={() => setAddMemberOpen(true)}
          >
            添加成员
          </Button>
        }
        width={600}
      >
        <List
          size="small"
          dataSource={detailQuery.data?.members ?? []}
          locale={{ emptyText: "暂无成员" }}
          renderItem={(member) => (
            <List.Item
              actions={[
                <Popconfirm
                  key="rm"
                  title="确定移除此成员？"
                  onConfirm={() => handleRemoveMember(member.user_id)}
                >
                  <Button size="small" danger>
                    移除
                  </Button>
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                title={member.display_name}
                description={`@${member.username}`}
              />
            </List.Item>
          )}
        />
      </Modal>

      {/* Add Member Modal */}
      <Modal
        title="添加成员"
        open={addMemberOpen}
        onOk={handleAddMembers}
        onCancel={() => {
          setAddMemberOpen(false);
          addForm.resetFields();
        }}
      >
        <Form form={addForm} layout="vertical">
          <Form.Item
            name="user_ids"
            label="选择用户"
            rules={[{ required: true, message: "请选择至少一个用户" }]}
          >
            <select multiple style={{ width: "100%", minHeight: 120 }}>
              {availableUsers.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.display_name} (@{u.username})
                </option>
              ))}
            </select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
