import React, {useState} from 'react';
import {CloseOutlined, InboxOutlined, LinkOutlined} from '@ant-design/icons';
import {Button, Col, DatePicker, Input, Layout, message, Row, Space, Typography, Upload, type UploadFile} from 'antd';
import axios from 'axios';

const {Dragger} = Upload;
const {Title} = Typography;
const {RangePicker} = DatePicker;
const {Content} = Layout;

const App: React.FC = () => {
    const [fileList, setFileList] = useState<UploadFile[]>([]); // 存储上传的文件列表
    const [processedResults, setProcessedResults] = useState<{
        patentResults: string[];
        paperResults: string[];
        unrecognizedResults: string[];
    }>({
        patentResults: [],
        paperResults: [],
        unrecognizedResults: [],
    });
    const [selectedTimeRange, setSelectedTimeRange] = useState<[string, string] | null>(null);
    const [timeCheckResult, setTimeCheckResult] = useState<string | null>(null);
    const [uploading, setUploading] = useState(false);
    const [extractedDocs, setExtractedDocs] = useState<{
        paperData: Record<string, any>; // 论文数据，键为文档 ID，值为对应的文档内容
        patentData: Record<string, any>; // 专利数据，键为文档 ID，值为对应的文档内容
    }>({
        paperData: {}, // 初始化为空对象
        patentData: {}, // 初始化为空对象
    });
    const [timeCheckPaperResult, setTimeCheckPaperResult] = useState<string | null>(null); // 存储符合条件的论文结果
    const [timeCheckPatentResult, setTimeCheckPatentResult] = useState<string | null>(null); // 存储符合条件的专利结果
    const [urlInput, setUrlInput] = useState(''); // 存储用户输入的URL
    const uploadProps = {
        name: 'file',
        multiple: true,
        beforeUpload: (file: UploadFile) => {
            if (file.size === 0) {
                message.error('文件为空，请检查后重新上传！');
                return false;
            }
            // console.log(`文件名：${file.name} 文件大小: ${file.size}, 文件类型: ${file.type}`);
            setFileList((prev) => [...prev, file]);
            return false;
        },
    };
    const handleUrlInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        setUrlInput(e.target.value);
    };

    // 添加URL文件
    const handleAddUrl = () => {
        if (!urlInput) {
            message.warning('请输入有效的URL！');
            return;
        }

        try {
            // 验证URL格式
            new URL(urlInput);
        } catch (e) {
            message.error('请输入有效的URL格式！');
            return;
        }

        // 从URL中提取文件名，如果没有则使用默认名
        const getDecodedFilename = (url: string) => {
            try {
                // 获取URL最后一部分（文件名）
                const encodedFilename = url.split('/').pop() || '';
                // 解码百分号编码（如%E6%95%B0%E5%AD%97 → "数字"）
                let decodedFilename = decodeURIComponent(encodedFilename);

                // 移除可能存在的查询参数（如?xxx=yyy）
                decodedFilename = decodedFilename.split('?')[0];
                // 移除可能存在的哈希参数（如#zzz）
                decodedFilename = decodedFilename.split('#')[0];

                // 如果解码后为空，使用默认名
                return decodedFilename || `下载文件-${Date.now()}.pdf`;
            } catch (e) {
                // 如果解码失败（如无效编码），使用原始文件名
                console.error('文件名解码失败:', e);
                return url.split('/').pop() || `下载文件-${Date.now()}.pdf`;
            }
        };

        const fileName = getDecodedFilename(urlInput);

        // 创建一个符合常规文件格式的对象
        const urlFile: UploadFile = {
            uid: `url-${Date.now()}`,
            name: fileName,  // 使用提取或生成的文件名
            size: 0,
            type: 'url',
            status: 'done',
            url: urlInput,  // 保留原始URL
        };
        setFileList((prev) => [...prev, urlFile]);
        setUrlInput('');
        message.success('URL已添加！');
    };

    const handleRemoveItem = (uid: string) => {
        setFileList((prev) => prev.filter((item) => item.uid !== uid));
    };

    // 点击上传按钮时触发的逻辑
    const handleUpload = async () => {
        if (fileList.length === 0) {
            message.warning('请先选择文件！');
            return;
        }
        setUploading(true); // 开始上传时设置按钮为加载状态
        try {
            const formData = new FormData();
            fileList.forEach((file) => {
                // 对于URL文件，创建一个包含URL信息的Blob对象
                if (file.type === 'url') {
                    const urlInfo = {
                        url: file.url,
                        name: file.name,
                        type: 'url'
                    };
                    const blob = new Blob([JSON.stringify(urlInfo)], {
                        type: 'application/json'
                    });
                    formData.append('files', blob, file.name);
                } else {
                    // 普通文件直接添加
                    if (file.originFileObj instanceof Blob) {
                        formData.append('files', file.originFileObj, file.name);
                    } else {
                        // 如果originFileObj不存在，尝试从file对象创建Blob
                        const blob = new Blob([file as any], {type: file.type});
                        formData.append('files', blob, file.name);
                    }
                }
            });
            // console.log('最终提交的FormData内容:');
            // for (const [key, value] of formData.entries()) {
            //     console.log(key, value);
            // }

            // 发送 POST 请求到后端服务
            const response = await axios.post('http://127.0.0.1:8000/api/v1/process_files', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data', // 确保使用正确的 Content-Type
                },
                validateStatus: (status) => status < 500
            });
            console.log(response);

            if (response.status === 400) {
                const errorData = response.data?.detail || response.data;
                throw {
                    isAxiosError: true,
                    response: {
                        status: 400,
                        data: errorData
                    }
                };
            }
            if (response.data && response.data.results && response.data.data) {
                const results = response.data.results; // 处理结果
                const data = response.data.data; // 结构化数据

                // 分类结果
                const patentResults: string[] = [];
                const paperResults: string[] = [];
                const unrecognizedResults: string[] = [];


                const paperData: Record<string, any> = {}; // 论文数据
                const patentData: Record<string, any> = {}; // 专利数据

                Object.keys(data).forEach((id) => {
                    const item = data[id]; // 获取每个文档的结构化数据
                    const result = results[id]; // 获取对应的处理结果字符串

                    if (item.类型 === '专利') {
                        patentResults.push(result);
                        patentData[id] = item; // 将专利数据存入字典
                    } else if (item.类型 === '论文') {
                        paperResults.push(result);
                        paperData[id] = item; // 将论文数据存入字典
                    } else {
                        unrecognizedResults.push(result);
                    }
                });

                setProcessedResults({
                    patentResults,
                    paperResults,
                    unrecognizedResults,
                });

                setExtractedDocs({
                    paperData,
                    patentData,
                });

                message.success('文件上传成功并处理完成！');
            } else {
                message.error('后端未返回处理结果，请检查后端代码！');
            }
        } catch (error: any) {
            // 修改：增强错误处理
            if (axios.isAxiosError(error)) {
                const errorData = error.response?.data?.detail || error.response?.data;

                if (error.response?.status === 400 && errorData?.error === 'URL_DOWNLOAD_FAILED') {
                    message.error(`文件下载失败: ${errorData.message}`);
                    // 标记失败文件
                    setFileList(prev => prev.map(f =>
                        f.name === errorData.filename ? {
                            ...f,
                            status: 'error',
                            response: errorData.message
                        } : f
                    ));
                } else {
                    message.error(errorData?.message || '文件处理失败');
                }
            } else {
                message.error(error.message || '网络错误');
            }
        } finally {
            setUploading(false);
        }
    };
    // 时间选择框的回调
    const handleTimeChange = (dates: any, dateStrings: [string, string]) => {
        setSelectedTimeRange(dateStrings);
    };

    const checkValidity = async () => {
        if (!selectedTimeRange) {
            message.warning('请先选择时间范围！');
            return;
        }
        if (!extractedDocs || (Object.keys(extractedDocs.paperData).length === 0 && Object.keys(extractedDocs.patentData).length === 0)) {
            message.warning('请先提取文档信息！');
            return;
        }
        console.log(extractedDocs);
        try {
            // 调用后端接口，传递 start_date、end_date 和 docs 参数
            const response = await axios.post('http://127.0.0.1:8000/api/v1/check_validity', {
                start_date: selectedTimeRange[0], // 起始日期
                end_date: selectedTimeRange[1],  // 结束日期
                docs: extractedDocs, // 前一个调用的结果（文档结构化信息）
            });

            if (response.data) {
                const {valid_papers, valid_patents} = response.data;

                // 更新状态，将论文和专利的结果分别存储
                const paperResults = valid_papers.map((doc: any, index: number) => (
                    <p key={index}>
                        文件名: {doc["文件名"]}, 标题: {doc["标题"]}, 作者: {doc["作者"]}, DOI: {doc["DOI"]},
                        收稿日期: {doc["received_date"]}, 接受日期: {doc["accepted_date"]},
                        出版日期: {doc["published_date"]}
                    </p>
                ));
                const patentResults = valid_patents.map((doc: any, index: number) => (
                    <p key={index}>
                        文件名: {doc["文件名"]}, 专利号: {doc["专利号"]}, 发明人: {doc["发明人"]},
                        受让人: {doc["受让人"]},
                        申请日期: {doc["申请日期"]}, 授权日期: {doc["授权日期"]}
                    </p>
                ));

                setTimeCheckPaperResult(paperResults); // 更新论文结果
                setTimeCheckPatentResult(patentResults); // 更新专利结果

                message.success(`时间范围检查完成，总计有效文档: ${response.data.total_valid}`);
            } else {
                message.error('后端未返回有效文档结果，请检查后端代码！');
            }
        } catch (error) {
            console.error('检查有效性失败:', error);
            message.error('检查有效性失败，请重试！');
        }
    };


    return (
        <Layout style={{height: '98vh', width: '100vw', padding: '16px'}}>
            <Content style={{padding: '16px'}}>
                <Row gutter={[16, 16]} style={{height: '100%'}}>
                    {/* 左侧上传区域 */}
                    <Col span={8} style={{
                        border: '1px solid #d9d9d9',
                        padding: '16px',
                        display: 'flex',
                        flexDirection: 'column',
                        height: '100%',
                        // justifyContent: 'space-between',
                    }}>
                        <Title level={5}>上传框</Title>
                        <div
                            style={{
                                margin: '16px 0',
                                padding: '0',
                                height: '200px', // 固定高度
                                // display: 'flex',
                                // flexDirection: 'column',
                            }}
                        >
                            <Dragger
                                showUploadList={false}
                                {...uploadProps}
                            >
                                <p className="ant-upload-drag-icon">
                                    <InboxOutlined/>
                                </p>
                                <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                                <p className="ant-upload-hint">支持单个或批量上传。</p>
                            </Dragger>
                        </div>
                        <div style={{marginBottom: '16px'}}>
                            <Title level={5} style={{marginBottom: '8px'}}>或输入URL</Title>
                            <Space.Compact style={{width: '100%'}}>
                                <Input
                                    placeholder="输入文件URL"
                                    prefix={<LinkOutlined/>}
                                    value={urlInput}
                                    onChange={handleUrlInput}
                                />
                                <Button type="primary" onClick={handleAddUrl}>
                                    添加
                                </Button>
                            </Space.Compact>
                        </div>
                        <Title level={5}>已添加项</Title>
                        <div style={{
                            border: '1px dashed #d9d9d9',
                            borderRadius: '4px',
                            padding: '8px',
                            maxHeight: '40vh',
                            overflowY: 'auto',
                            marginBottom: '16px'
                        }}>
                            {fileList.length === 0 ? (
                                <div style={{color: 'rgba(0, 0, 0, 0.25)', textAlign: 'center'}}>暂无内容</div>
                            ) : (
                                <div style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
                                    {fileList.map(item => (
                                        <div key={item.uid} style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                            padding: '4px 8px',
                                            backgroundColor: '#fafafa',
                                            borderRadius: '4px'
                                        }}>
                                            <span style={{flex: 1, overflow: 'hidden', textOverflow: 'ellipsis'}}>
                                                {item.type === 'url' ? (
                                                    <LinkOutlined style={{marginRight: '8px', color: '#1890ff'}}/>
                                                ) : (
                                                    <InboxOutlined style={{marginRight: '8px'}}/>
                                                )}
                                                {item.name}
                                            </span>
                                            <Button
                                                type="text"
                                                icon={<CloseOutlined/>}
                                                onClick={() => handleRemoveItem(item.uid)}
                                                size="small"
                                            />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <Button
                            type="primary"
                            onClick={handleUpload}
                            loading={uploading} // 按钮的加载状态
                            style={{justifyContent: 'center', bottom: '0'}}
                        >
                            {uploading ? '处理中...' : '上传'}
                        </Button>
                    </Col>

                    {/* 右侧结果与时间选择区域 */}
                    <Col span={16} style={{padding: '16px'}}>
                        <Row style={{height: '50%', marginBottom: '16px'}}>
                            <Col span={8}>
                                <Title level={5}>论文结果</Title>
                                <div style={{
                                    border: '1px solid #d9d9d9',
                                    height: '38vh',
                                    overflow: 'auto',
                                    padding: '8px'
                                }}>
                                    {processedResults.paperResults.length > 0 ? (
                                        processedResults.paperResults.map((result, index) => <p
                                            key={index}>{result}</p>)
                                    ) : (
                                        <p>暂无论文结果</p>
                                    )}
                                </div>
                            </Col>
                            <Col span={8}>
                                <Title level={5}>专利结果</Title>
                                <div style={{
                                    border: '1px solid #d9d9d9',
                                    height: '38vh',
                                    overflow: 'auto',
                                    padding: '8px'
                                }}>
                                    {processedResults.patentResults.length > 0 ? (
                                        processedResults.patentResults.map((result, index) => <p
                                            key={index}>{result}</p>)
                                    ) : (
                                        <p>暂无专利结果</p>
                                    )}
                                </div>
                            </Col>
                            <Col span={8}>
                                <Title level={5}>其他文件结果</Title>
                                <div style={{
                                    border: '1px solid #d9d9d9',
                                    height: '38vh',
                                    overflow: 'auto',
                                    padding: '8px'
                                }}>
                                    {processedResults.unrecognizedResults.length > 0 ? (
                                        processedResults.unrecognizedResults.map((result, index) => <p
                                            key={index}>{result}</p>)
                                    ) : (
                                        <p>暂无结果</p>
                                    )}
                                </div>
                            </Col>
                        </Row>
                        <Row style={{
                            marginTop: "10px",
                            display: 'flex',
                            alignItems: 'center'
                        }}>
                            <Col span={20}>
                                <Space direction="horizontal" size={12}>
                                    选择有效时间:<RangePicker onChange={handleTimeChange}/>
                                </Space>
                            </Col>
                            <Col span={4}>
                                <Button type="primary" onClick={checkValidity} style={{justifyContent: "center"}}>
                                    检查有效文档
                                </Button>
                            </Col>
                        </Row>
                        <Row style={{height: '35%', paddingTop: '16px'}}>
                            <Col span={12} style={{paddingRight: '8px'}}>
                                <Title level={5}>符合条件的论文</Title>
                                <div style={{
                                    border: '1px solid #d9d9d9',
                                    height: '100%',
                                    overflow: 'auto',
                                    padding: '8px'
                                }}>
                                    {timeCheckPaperResult ? timeCheckPaperResult : <p>暂无符合条件的论文结果</p>}
                                </div>
                            </Col>
                            <Col span={12} style={{paddingLeft: '8px'}}>
                                <Title level={5}>符合条件的专利</Title>
                                <div style={{
                                    border: '1px solid #d9d9d9',
                                    height: '100%',
                                    overflow: 'auto',
                                    padding: '8px'
                                }}>
                                    {timeCheckPatentResult ? timeCheckPatentResult : <p>暂无符合条件的专利结果</p>}
                                </div>
                            </Col>
                        </Row>
                    </Col>
                </Row>
            </Content>
        </Layout>
    );
};

export default App;
